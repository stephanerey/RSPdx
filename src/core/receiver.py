from __future__ import annotations

import logging
import numpy as np
from typing import Optional, Callable
import threading
import time
from PyQt5 import QtCore
from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot
from scipy.signal import lfilter

from src.core.demodulators import FMAudioMode, build_demodulator_registry

from .dsp import design_lpf_fir, mix_to_baseband_block, streaming_decimate
from .dsp.resampler import RationalResampler

# =========================================================
#                        LOGS
# =========================================================
DEBUG_RX = False  # passe à True pour diagnostiquer
LOGGER = logging.getLogger("RSPdx.Receiver")


def _log_rx(*args):
    if not DEBUG_RX:
        return
    ts = QtCore.QTime.currentTime().toString("HH:mm:ss.zzz")
    LOGGER.debug("[RX][%s] %s", ts, " ".join(str(arg) for arg in args))


# =========================================================
#                      RECEIVER
# =========================================================
class Receiver(QObject):
    """
    Chaîne sous-bande (par RX) :
      mixer(f_offset) -> LPF(FIR) -> decim (entière) -> (Costas optionnel)
      -> envoi vers démodulateur (par ex. FM) en bande de base à fs_bb
    """

    # Signaux utiles pour le reste de l'app
    iq_out = pyqtSignal(np.ndarray)        # flux IQ post-traitement (complex64)
    frequency_changed = pyqtSignal(float)  # fréquence absolue sélectionnée (Hz)
    bandwidth_changed = pyqtSignal(float)  # BW (Hz)
    quality_updated = pyqtSignal(dict)     # lock/EVM/qualité symbole
    demodulator_changed = pyqtSignal(str)
    audio_state_changed = pyqtSignal(bool)
    perf_updated = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(
        self,
        name: str,
        sample_rate: float,
        center_freq_provider: Callable[[], float],  # callable -> fréquence centrale SDR (Hz)
        selected_freq: float,
        bandwidth: float = 25e3,
        enable_costas: bool = False,
        costas_mode: str = "qpsk",
        num_taps: int = 511,
        parent: Optional[QObject] = None,
    ):
        super().__init__(parent)

        self.name = str(name)

        # Réglages courants du RX
        self.sample_rate = float(sample_rate)       # FS matérielle du SDR (input de ce RX)
        self._selected_freq = float(selected_freq)  # fréquence absolue à viser
        self._bandwidth = float(bandwidth)          # largeur de bande (pour le FIR)
        self._center_freq_provider = center_freq_provider

        # Options DSP
        self.enable_costas = bool(enable_costas)
        self.costas_mode = str(costas_mode)
        self.num_taps = int(num_taps)

        # État DSP sous-bande
        self._pre_decim = 1
        self._pre_residual = np.zeros(0, dtype=np.complex64)
        self._decim = 1                    # facteur entier de décimation (input -> bb)
        self._fs_bb = float(sample_rate)   # fs après décimation
        self._taps_cache = None
        self._taps_bw = None
        self._taps_fs = None
        self._fir_zi = None
        self._mix_phase = 0.0
        self._decim_phase = 0
        self._sym_phase = 0.0
        self._costas_phase = 0.0
        self._costas_freq = 0.0
        self._costas_active_last = False
        self.costas_loop_bw = 0.02
        self.costas_damping = 0.707
        self._prev_const_sample = None
        self._iq_rho = 0.0 + 0.0j
        self._iq_alpha = 0.05
        self._timing_gain = 0.008
        self._timing_conf = 0.0
        self._timing_reacq_ctr = 0
        self._ted_mean = 0.0
        self._ted_std = 0.0
        self._timing_corr_norm = 0.0
        self._timing_clip_events = 0
        self._sps_offset = 0.0
        self._eq_enabled = False
        self._eq_mu = 0.00025
        self._eq_ntaps = 7
        self._eq_w = None
        self._eq_buf = None
        self._eq_err_rms = 0.0
        self._eq_upd_norm = 0.0
        self._last_quality_emit = 0.0
        self._quality_interval_s = 0.20
        self._perf_interval_s = 1.0
        self._perf_last_emit_at = time.monotonic()
        self._perf_blocks = 0
        self._perf_input_samples = 0
        self._perf_baseband_samples = 0
        self._perf_process_time_s = 0.0
        self._perf_process_time_max_s = 0.0
        self._perf_demod_time_s = 0.0
        self._perf_demod_time_max_s = 0.0

        # Démodulateur (ex: FMDemodulator)
        self.demod = None
        self.demod_mode = "fm"
        self.demod_enabled = False
        self.audio_enabled = False
        self._audio_output_device = None
        self._demodulator_registry = build_demodulator_registry()

        # Constellation
        self.constellation_mode = "raw"   # "raw" | "symbols"
        self.constellation_domain = "iq"  # "iq" | "differential"
        self.symbol_rate = 18_000.0       # Hz (utile en mode symbols)
        self.iq_correction_enabled = True
        self.modulation_profile = "generic"  # "generic" | "tetra"
        self._rrc_rolloff = 0.35
        self._rrc_span_symbols = 8
        self._rrc_sps_design = 4
        self._rrc_taps = None
        self._rrc_zi = None
        self._tetra_rs_i = None
        self._tetra_rs_q = None
        self._tetra_rs_in = 0.0
        self._tetra_rs_out = 0.0

        # petit timer pour éviter de redesigner le FIR à chaque pixel de slider BW
        self._bw_timer = QtCore.QTimer(self)
        self._bw_timer.setSingleShot(True)
        self._bw_timer.setInterval(120)  # ms
        self._bw_timer.timeout.connect(self._apply_bw_params)

        # Flags de fonctionnement/reconfig
        self._running = True
        self._reconfig = threading.Event()
        self._last_fs = None

        # Premier calcul de chaîne sous-bande
        self._apply_bw_params()

        _log_rx(
            f"{self.name}: init fs={self.sample_rate:.1f} Hz, sel_f={self._selected_freq:.0f} Hz, "
            f"BW={self._bandwidth/1e3:.1f} kHz, decim={self._decim}, fs_bb≈{self._fs_bb:.1f}"
        )

    # ----------------------- API -----------------------
    def set_demodulator(self, demod):
        """
        Assigne (ou remplace) le démodulateur pour ce RX.
        On pousse immédiatement le fs_bb courant au démod.
        """
        self.demod = demod
        _log_rx(f"{self.name}: set_demodulator -> {type(demod).__name__ if demod else 'None'}")
        if self.demod is not None:
            try:
                self.demod.set_input_rate(self._fs_bb)
            except Exception as e:
                _log_rx(f"{self.name}: demod.set_input_rate error: {e!r}")

    def _build_demodulator(self, demod_mode: str):
        mode = str(demod_mode).lower()
        if mode == "fm":
            return self._demodulator_registry["fm"](
                audio_rate=48_000,
                deemph_us=50.0,
                mode=FMAudioMode.NARROW,
            )
        factory = self._demodulator_registry.get(mode)
        if factory is None:
            factory = self._demodulator_registry["fm"]
            mode = "fm"
        return factory()

    def _emit_error(self, message: str) -> None:
        LOGGER.error("%s: %s", self.name, message)
        self.error.emit(message)

    def _start_demod_audio(self, output_device=None) -> None:
        if self.demod is None:
            self.demod = self._build_demodulator(self.demod_mode)
            self.demod.set_input_rate(self._fs_bb)
        self.demod.start(output_device=output_device)
        self.audio_enabled = True
        self.audio_state_changed.emit(True)

    def _stop_demod_audio(self) -> None:
        if self.demod is not None:
            self.demod.stop()
        self.audio_enabled = False
        self.audio_state_changed.emit(False)

    @pyqtSlot(str)
    def set_demod_mode(self, demod_mode: str):
        mode = str(demod_mode).lower()
        old_demod = self.demod
        old_running = bool(getattr(old_demod, "_running", False)) or bool(self.audio_enabled)
        if old_demod is not None:
            try:
                old_demod.stop()
            except Exception:
                pass

        try:
            new_demod = self._build_demodulator(mode)
            new_demod.set_input_rate(self._fs_bb)
        except Exception as exc:
            self._emit_error(f"Unable to create demodulator '{mode}': {exc}")
            return

        self.demod = new_demod
        self.demod_mode = mode
        self.demodulator_changed.emit(mode)

        if old_running:
            try:
                self._start_demod_audio(self._audio_output_device)
            except Exception as exc:
                self.audio_enabled = False
                self.audio_state_changed.emit(False)
                self._emit_error(f"Audio start failed: {exc}")

    @pyqtSlot(bool)
    def set_audio_enabled(self, enabled: bool):
        enabled = bool(enabled)
        if enabled:
            try:
                self._start_demod_audio(self._audio_output_device)
            except Exception as exc:
                self.audio_enabled = False
                self.audio_state_changed.emit(False)
                self._emit_error(f"Audio start failed: {exc}")
        else:
            try:
                self._stop_demod_audio()
            except Exception as exc:
                self._emit_error(f"Audio stop failed: {exc}")

    @pyqtSlot(int)
    def set_audio_output_device(self, device_index: int):
        self._audio_output_device = None if int(device_index) < 0 else int(device_index)
        if self.demod is None:
            return
        if bool(getattr(self.demod, "_running", False)) or bool(self.audio_enabled):
            try:
                self.demod.stop()
                self._start_demod_audio(self._audio_output_device)
            except Exception as exc:
                self.audio_enabled = False
                self.audio_state_changed.emit(False)
                self._emit_error(f"Audio device switch failed: {exc}")

    @pyqtSlot()
    def shutdown(self):
        self._running = False
        self._reconfig.set()
        try:
            if self._bw_timer.isActive():
                self._bw_timer.stop()
            self._stop_demod_audio()
        except Exception:
            pass

    def _emit_perf_snapshot(self, now: float) -> None:
        elapsed = now - self._perf_last_emit_at
        if elapsed < self._perf_interval_s:
            return

        demod_stats = {}
        if self.demod is not None and hasattr(self.demod, "get_runtime_stats"):
            try:
                demod_stats = dict(self.demod.get_runtime_stats())
            except Exception:
                demod_stats = {}

        snapshot = {
            "name": self.name,
            "demod_mode": str(self.demod_mode).upper(),
            "audio_enabled": bool(self.audio_enabled),
            "selected_freq_hz": float(self._selected_freq),
            "bandwidth_hz": float(self._bandwidth),
            "sample_rate_hz": float(self.sample_rate),
            "baseband_rate_hz": float(self._fs_bb),
            "iq_block_rate_hz": self._perf_blocks / max(elapsed, 1e-9),
            "input_msample_s": self._perf_input_samples / max(elapsed, 1e-9) / 1_000_000.0,
            "baseband_ksample_s": self._perf_baseband_samples / max(elapsed, 1e-9) / 1_000.0,
            "process_avg_ms": 1000.0 * self._perf_process_time_s / max(1, self._perf_blocks),
            "process_max_ms": 1000.0 * self._perf_process_time_max_s,
            "demod_avg_ms": 1000.0 * self._perf_demod_time_s / max(1, self._perf_blocks),
            "demod_max_ms": 1000.0 * self._perf_demod_time_max_s,
            "thread_name": getattr(self, "_thread_name", self.name),
        }
        snapshot.update(demod_stats)
        self.perf_updated.emit(snapshot)
        self._perf_last_emit_at = now
        self._perf_blocks = 0
        self._perf_input_samples = 0
        self._perf_baseband_samples = 0
        self._perf_process_time_s = 0.0
        self._perf_process_time_max_s = 0.0
        self._perf_demod_time_s = 0.0
        self._perf_demod_time_max_s = 0.0

    @pyqtSlot()
    def reset_runtime_stats(self) -> None:
        self._perf_last_emit_at = time.monotonic()
        self._perf_blocks = 0
        self._perf_input_samples = 0
        self._perf_baseband_samples = 0
        self._perf_process_time_s = 0.0
        self._perf_process_time_max_s = 0.0
        self._perf_demod_time_s = 0.0
        self._perf_demod_time_max_s = 0.0
        if self.demod is not None and hasattr(self.demod, "reset_runtime_stats"):
            try:
                self.demod.reset_runtime_stats()
            except Exception:
                pass

    def _record_perf(self, input_samples: int, baseband_samples: int, process_time_s: float, demod_time_s: float) -> None:
        self._perf_blocks += 1
        self._perf_input_samples += int(max(0, input_samples))
        self._perf_baseband_samples += int(max(0, baseband_samples))
        self._perf_process_time_s += float(max(0.0, process_time_s))
        self._perf_process_time_max_s = max(self._perf_process_time_max_s, float(max(0.0, process_time_s)))
        self._perf_demod_time_s += float(max(0.0, demod_time_s))
        self._perf_demod_time_max_s = max(self._perf_demod_time_max_s, float(max(0.0, demod_time_s)))
        self._emit_perf_snapshot(time.monotonic())

    @pyqtSlot(float)
    def set_sample_rate(self, fs_hz: float):
        """
        Appelée quand la FS matérielle du SDR change.
        Thread-safe via _reconfig: bloque process_block pendant la recomposition de chaîne.
        """
        self._reconfig.set()
        try:
            self.sample_rate = float(fs_hz)
            _log_rx(f"{self.name}: set_sample_rate({self.sample_rate:.1f})")

            # prévenir le démod (mute doux)
            if self.demod is not None and hasattr(self.demod, "begin_reconfig"):
                try:
                    self.demod.begin_reconfig(mute_sec=0.25)
                except Exception as e:
                    _log_rx(f"{self.name}: demod.begin_reconfig error: {e!r}")

            # recalcul complet de la chaîne sous-bande
            self._apply_bw_params()
        finally:
            self._reconfig.clear()

    # ------------------- Propriétés --------------------
    @property
    def selected_freq(self) -> float:
        return self._selected_freq

    @property
    def bandwidth(self) -> float:
        return self._bandwidth

    # ------------------ Setters/slots ------------------
    @pyqtSlot(float)
    def on_sample_rate_about_to_change(self, new_fs: float):
        """
        Optionnel: si tu connectes SDRController.sample_rate_about_to_change → ce slot,
        on peut “muter” le démod un poil avant le cut du flux IQ.
        """
        self._reconfig.set()
        if self.demod is not None and hasattr(self.demod, "begin_reconfig"):
            try:
                self.demod.begin_reconfig(mute_sec=0.25)
            except Exception as e:
                _log_rx(f"{self.name}: begin_reconfig(about_to_change) error: {e!r}")

    @pyqtSlot(float)
    def set_selected_frequency(self, f_hz: float):
        self._selected_freq = float(f_hz)
        self.frequency_changed.emit(self._selected_freq)
        _log_rx(f"{self.name}: selected_freq -> {self._selected_freq:.0f} Hz")

    @pyqtSlot(float)
    def set_bandwidth(self, bw_hz: float):
        self._bandwidth = max(1.0, float(bw_hz))
        _log_rx(f"{self.name}: set_bandwidth({self._bandwidth/1e3:.1f} kHz)")

        # mute court côté démod pendant la reconfig
        if self.demod is not None and hasattr(self.demod, "begin_reconfig"):
            try:
                self.demod.begin_reconfig(mute_sec=0.20)
            except Exception as e:
                _log_rx(f"{self.name}: demod.begin_reconfig error: {e!r}")

        # debounce du redesign FIR
        if self._bw_timer.isActive():
            self._bw_timer.stop()
        self._bw_timer.start()

        self.bandwidth_changed.emit(self._bandwidth)

    @pyqtSlot(str)
    def set_constellation_mode(self, mode: str):
        m = str(mode).strip().lower()
        if m not in ("raw", "symbols"):
            m = "raw"
        self.constellation_mode = m
        self._sym_phase = 0.0
        self._reset_constellation_state()
        _log_rx(f"{self.name}: constellation_mode -> {self.constellation_mode}")

    @pyqtSlot(float)
    def set_symbol_rate(self, symbol_rate_hz: float):
        self.symbol_rate = max(1.0, float(symbol_rate_hz))
        self._sym_phase = 0.0
        self._reset_constellation_state()
        # En profil TETRA, la BW utile dépend du symbol rate -> reconfig DSP.
        if self.modulation_profile == "tetra":
            self._reconfig.set()
            try:
                self._apply_bw_params()
            finally:
                self._reconfig.clear()
        _log_rx(f"{self.name}: symbol_rate -> {self.symbol_rate:.1f} Hz")

    @pyqtSlot(str)
    def set_modulation_profile(self, profile: str):
        p = str(profile).strip().lower()
        if p not in ("generic", "tetra"):
            p = "generic"
        self._reconfig.set()
        try:
            self.modulation_profile = p
            if p == "tetra":
                self.symbol_rate = 18_000.0
                self._timing_gain = 0.0018
                self.enable_costas = True
                self.costas_mode = "qpsk"
                self.iq_correction_enabled = True
                self.costas_loop_bw = 0.008
                # EQ adaptatif désactivé: il déstabilise encore la chaîne.
                self._eq_enabled = False
            else:
                self._timing_gain = 0.008
                self.costas_loop_bw = 0.02
                self._eq_enabled = False

            if self.demod is not None and hasattr(self.demod, "begin_reconfig"):
                try:
                    self.demod.begin_reconfig(mute_sec=0.15)
                except Exception:
                    pass

            self._rrc_taps = None
            self._rrc_zi = None
            self._tetra_rs_i = None
            self._tetra_rs_q = None
            self._tetra_rs_in = 0.0
            self._tetra_rs_out = 0.0
            self._reset_equalizer_state()
            self._sym_phase = 0.0
            self._reset_constellation_state()

            # IMPORTANT: recalc décim/fs_bb/filter immédiatement.
            self._apply_bw_params()
        finally:
            self._reconfig.clear()
        _log_rx(f"{self.name}: modulation_profile -> {self.modulation_profile}")

    @pyqtSlot(str)
    def set_constellation_domain(self, domain: str):
        d = str(domain).strip().lower()
        if d not in ("iq", "differential"):
            d = "iq"
        self.constellation_domain = d
        self._reset_constellation_state()
        _log_rx(f"{self.name}: constellation_domain -> {self.constellation_domain}")

    @pyqtSlot(bool)
    def set_iq_correction_enabled(self, enabled: bool):
        self.iq_correction_enabled = bool(enabled)
        self._iq_rho = 0.0 + 0.0j
        _log_rx(f"{self.name}: iq_correction_enabled -> {self.iq_correction_enabled}")

    @pyqtSlot(bool)
    def set_costas_enabled(self, enabled: bool):
        self.enable_costas = bool(enabled)
        self._reset_costas_state()
        _log_rx(f"{self.name}: costas enabled -> {self.enable_costas}")

    @pyqtSlot(str)
    def set_costas_mode(self, mode: str):
        m = str(mode).strip().lower()
        if m not in ("qpsk", "bpsk"):
            m = "qpsk"
        self.costas_mode = m
        self._reset_costas_state()
        _log_rx(f"{self.name}: costas mode -> {self.costas_mode}")

    def _reset_costas_state(self):
        self._costas_phase = 0.0
        self._costas_freq = 0.0
        self._costas_active_last = False

    def _reset_constellation_state(self):
        self._prev_const_sample = None
        self._timing_conf = 0.0
        self._timing_reacq_ctr = 0
        self._ted_mean = 0.0
        self._ted_std = 0.0
        self._timing_corr_norm = 0.0
        self._timing_clip_events = 0
        self._sps_offset = 0.0
        self._reset_equalizer_state()

    def _reset_equalizer_state(self):
        nt = int(max(3, self._eq_ntaps))
        if (nt % 2) == 0:
            nt += 1
        self._eq_w = np.zeros(nt, dtype=np.complex64)
        self._eq_w[nt // 2] = 1.0 + 0.0j
        self._eq_buf = np.zeros(nt, dtype=np.complex64)
        self._eq_err_rms = 0.0
        self._eq_upd_norm = 0.0

    @staticmethod
    def _design_rrc_taps(alpha: float, sps: int, span_symbols: int) -> np.ndarray:
        alpha = float(alpha)
        sps = int(max(2, sps))
        span_symbols = int(max(4, span_symbols))
        n_taps = span_symbols * sps * 2 + 1
        t = np.arange(-(n_taps // 2), n_taps // 2 + 1, dtype=np.float64) / sps
        h = np.zeros_like(t)

        for i, ti in enumerate(t):
            if abs(ti) < 1e-12:
                h[i] = 1.0 - alpha + 4.0 * alpha / np.pi
                continue
            if alpha > 0 and abs(abs(4.0 * alpha * ti) - 1.0) < 1e-8:
                a = (1.0 + 2.0 / np.pi) * np.sin(np.pi / (4.0 * alpha))
                b = (1.0 - 2.0 / np.pi) * np.cos(np.pi / (4.0 * alpha))
                h[i] = (alpha / np.sqrt(2.0)) * (a + b)
                continue

            num1 = np.sin(np.pi * ti * (1.0 - alpha))
            num2 = 4.0 * alpha * ti * np.cos(np.pi * ti * (1.0 + alpha))
            den = np.pi * ti * (1.0 - (4.0 * alpha * ti) ** 2)
            if abs(den) < 1e-12:
                h[i] = 0.0
            else:
                h[i] = (num1 + num2) / den

        e = np.sqrt(np.sum(h * h))
        if e > 1e-12:
            h = h / e
        return h.astype(np.float32)

    def _ensure_rrc(self):
        if self.modulation_profile != "tetra":
            self._rrc_taps = None
            self._rrc_zi = None
            return
        if self._rrc_taps is not None and self._rrc_zi is not None:
            return
        self._rrc_taps = self._design_rrc_taps(
            alpha=self._rrc_rolloff,
            sps=self._rrc_sps_design,
            span_symbols=self._rrc_span_symbols
        )
        self._rrc_zi = np.zeros(max(0, len(self._rrc_taps) - 1), dtype=np.complex64)

    def _apply_rrc_streaming(self, x: np.ndarray) -> np.ndarray:
        if x is None or x.size == 0:
            return np.zeros(0, dtype=np.complex64)
        self._ensure_rrc()
        if self._rrc_taps is None:
            return x.astype(np.complex64, copy=False)
        zi = self._rrc_zi
        if zi is None or zi.size != max(0, len(self._rrc_taps) - 1):
            zi = np.zeros(max(0, len(self._rrc_taps) - 1), dtype=np.complex64)
        y, self._rrc_zi = lfilter(self._rrc_taps, [1.0], x, zi=zi)
        return y.astype(np.complex64, copy=False)

    def _apply_tetra_symbol_resample(self, x: np.ndarray, fs_in: float):
        """
        Force un fs_bb proche de 4*srate en profil TETRA pour stabiliser le TED.
        """
        if x is None or x.size == 0:
            return np.zeros(0, dtype=np.complex64), fs_in
        if self.modulation_profile != "tetra":
            return x.astype(np.complex64, copy=False), fs_in

        fs_out = float(max(10_000.0, 4.0 * self.symbol_rate))
        if abs(fs_in - fs_out) <= 1.0:
            return x.astype(np.complex64, copy=False), fs_in

        if self._tetra_rs_i is None or self._tetra_rs_q is None:
            self._tetra_rs_i = RationalResampler(fs_in, fs_out)
            self._tetra_rs_q = RationalResampler(fs_in, fs_out)
            self._tetra_rs_in = float(fs_in)
            self._tetra_rs_out = float(fs_out)
        else:
            changed = (
                abs(fs_in - self._tetra_rs_in) / max(1.0, self._tetra_rs_in) > 0.001 or
                abs(fs_out - self._tetra_rs_out) / max(1.0, self._tetra_rs_out) > 0.001
            )
            if changed:
                self._tetra_rs_i.set_ratio(fs_in, fs_out)
                self._tetra_rs_q.set_ratio(fs_in, fs_out)
                self._tetra_rs_in = float(fs_in)
                self._tetra_rs_out = float(fs_out)

        y_i = self._tetra_rs_i.process(np.real(x).astype(np.float32, copy=False))
        y_q = self._tetra_rs_q.process(np.imag(x).astype(np.float32, copy=False))
        n = min(y_i.size, y_q.size)
        if n <= 0:
            return np.zeros(0, dtype=np.complex64), fs_out
        y = y_i[:n].astype(np.float32) + 1j * y_q[:n].astype(np.float32)
        return y.astype(np.complex64, copy=False), fs_out

    @staticmethod
    def _interp_linear(x: np.ndarray, t: float):
        i0 = int(t)
        frac = float(t - i0)
        return (1.0 - frac) * x[i0] + frac * x[i0 + 1]

    @staticmethod
    def _sanitize_complex(x: np.ndarray, max_abs: float = 100.0) -> np.ndarray:
        if x is None or x.size == 0:
            return np.zeros(0, dtype=np.complex64)
        y = x.astype(np.complex64, copy=False)
        fin = np.isfinite(np.real(y)) & np.isfinite(np.imag(y))
        if not np.all(fin):
            y = y.copy()
            y[~fin] = 0.0 + 0.0j
        a = np.abs(y)
        if a.size:
            clip = a > float(max_abs)
            if np.any(clip):
                y = y.copy()
                y[clip] *= (float(max_abs) / (a[clip] + 1e-12))
        return y

    def _apply_iq_correction(self, x: np.ndarray) -> np.ndarray:
        if x is None or x.size < 2:
            return np.zeros(0, dtype=np.complex64)

        y = self._sanitize_complex(x, max_abs=100.0)
        y = y - np.mean(y)
        if not self.iq_correction_enabled:
            return y

        p = float(np.mean(np.abs(y) ** 2) + 1e-12)
        rho_est = np.mean(y * y) / p
        mag = float(np.abs(rho_est))
        if mag > 0.95:
            rho_est = rho_est * (0.95 / mag)

        self._iq_rho = (1.0 - self._iq_alpha) * self._iq_rho + self._iq_alpha * rho_est
        yc = y - self._iq_rho * np.conj(y)
        g = 1.0 - float(np.abs(self._iq_rho) ** 2)
        if g > 1e-6:
            yc = yc / np.sqrt(g)
        return yc.astype(np.complex64, copy=False)

    @staticmethod
    def _phase_histogram_quadrants(ph: np.ndarray) -> np.ndarray:
        if ph is None or ph.size == 0:
            return np.zeros(4, dtype=np.float32)
        ph = ph[np.isfinite(ph)]
        if ph.size == 0:
            return np.zeros(4, dtype=np.float32)
        c4 = np.mean(np.exp(1j * 4.0 * ph))
        phi = 0.25 * float(np.angle(c4 + 1e-12))
        pha = (ph - phi + np.pi) % (2.0 * np.pi) - np.pi
        idx = np.mod(np.floor((pha + np.pi / 4.0) / (np.pi / 2.0)).astype(np.int32), 4)
        h = np.bincount(idx, minlength=4).astype(np.float32)
        s = float(np.sum(h))
        if s > 0.0:
            h /= s
        return h

    @staticmethod
    def _qpsk_cluster_eccentricity(points: np.ndarray) -> float:
        if points is None or points.size < 48:
            return 0.0
        pr = Receiver._sanitize_complex(points, max_abs=20.0)
        if pr.size < 48:
            return 0.0
        phi = 0.25 * np.angle(np.mean(pr ** 4) + 1e-12)
        pr = pr * np.exp(-1j * phi)
        labels = (np.real(pr) >= 0.0).astype(np.int32) * 2 + (np.imag(pr) >= 0.0).astype(np.int32)
        ratios = []
        for k in range(4):
            pts = pr[labels == k]
            if pts.size < 10:
                continue
            xy = np.column_stack((np.real(pts), np.imag(pts))).astype(np.float64, copy=False)
            cov = np.cov(xy, rowvar=False)
            if cov.shape != (2, 2):
                continue
            w = np.linalg.eigvalsh(cov)
            w = np.sort(np.maximum(w, 1e-12))
            ratios.append(float(np.sqrt(w[1] / w[0])))
        if not ratios:
            return 0.0
        return float(np.mean(ratios))

    def _compute_quality(self, points: np.ndarray, fs_for_sps: Optional[float] = None) -> Optional[dict]:
        if points is None or points.size < 32:
            return None
        p = self._sanitize_complex(points, max_abs=20.0)
        if p.size < 32:
            return None
        rms = float(np.sqrt(np.mean(np.abs(p) ** 2)))
        if (not np.isfinite(rms)) or rms <= 1e-9:
            return None
        p = p / rms

        # Rejet des outliers pour une mesure plus robuste (bursts/échantillons faibles).
        mag = np.abs(p)
        med = float(np.median(mag)) if mag.size else 0.0
        if med > 1e-12:
            keep = (mag > 0.35 * med) & (mag < 2.5 * med)
            if np.count_nonzero(keep) >= 24:
                p = p[keep]

        mode = "bpsk" if self.costas_mode == "bpsk" else "qpsk"
        if mode == "bpsk":
            phi = 0.5 * np.angle(np.mean(p ** 2) + 1e-12)
            pr = p * np.exp(-1j * phi)
            pr = self._sanitize_complex(pr, max_abs=8.0)
            ideal = np.where(np.real(pr) >= 0.0, 1.0 + 0.0j, -1.0 + 0.0j).astype(np.complex64)
            c_metric = float(np.abs(np.mean((pr / (np.abs(pr) + 1e-12)) ** 2)))
            c_thr_lock = 0.75
            c_thr_weak = 0.55
        else:
            phi = 0.25 * np.angle(np.mean(p ** 4) + 1e-12)
            pr = p * np.exp(-1j * phi)
            pr = self._sanitize_complex(pr, max_abs=8.0)
            re = np.where(np.real(pr) >= 0.0, 1.0, -1.0)
            im = np.where(np.imag(pr) >= 0.0, 1.0, -1.0)
            ideal = ((re + 1j * im) / np.sqrt(2.0)).astype(np.complex64)
            c_metric = float(np.abs(np.mean((pr / (np.abs(pr) + 1e-12)) ** 4)))
            c_thr_lock = 0.70 if self.modulation_profile == "tetra" else 0.55
            c_thr_weak = 0.50
        if not np.isfinite(c_metric):
            c_metric = 0.0

        evm = float(
            np.sqrt(np.mean(np.abs(pr - ideal) ** 2)) /
            (np.sqrt(np.mean(np.abs(ideal) ** 2)) + 1e-12) * 100.0
        )
        if not np.isfinite(evm):
            evm = 999.0
        # Décomposition EVM: composante radiale (amplitude) vs tangentielle (phase/timing).
        e = (pr - ideal).astype(np.complex64, copy=False)
        u = (ideal / (np.abs(ideal) + 1e-12)).astype(np.complex64, copy=False)
        e_rad = np.real(e * np.conj(u)).astype(np.float32, copy=False)
        e_tan = np.imag(e * np.conj(u)).astype(np.float32, copy=False)
        evm_rad = float(np.sqrt(np.mean(e_rad * e_rad)) * 100.0)
        evm_tan = float(np.sqrt(np.mean(e_tan * e_tan)) * 100.0)
        if not np.isfinite(evm_rad):
            evm_rad = 999.0
        if not np.isfinite(evm_tan):
            evm_tan = 999.0
        evm_rt_ratio = float(evm_rad / max(1e-6, evm_tan))
        if not np.isfinite(evm_rt_ratio):
            evm_rt_ratio = 0.0
        if c_metric >= c_thr_lock and evm <= 40.0:
            state = "LOCK"
        elif c_metric >= c_thr_weak and evm <= 70.0:
            state = "WEAK"
        else:
            state = "SEARCH"

        lock = bool(state == "LOCK")
        fs_eff = float(fs_for_sps) if (fs_for_sps is not None and fs_for_sps > 0.0) else float(self._fs_bb)
        sps_nom = float(fs_eff / max(1.0, self.symbol_rate))
        sps = float(sps_nom + self._sps_offset)
        sps_off_ppm = float((self._sps_offset / max(1e-9, sps_nom)) * 1e6)
        evm_rms = max(1e-6, evm / 100.0)
        mer_db = float(-20.0 * np.log10(evm_rms))

        # CFO résiduel de la boucle Costas (rad/sample -> Hz).
        cfo_hz = float(self._costas_freq * fs_eff / (2.0 * np.pi))
        cfo_ppm = float(cfo_hz / max(1.0, abs(self._selected_freq)) * 1e6)
        if not np.isfinite(cfo_hz):
            cfo_hz = 0.0
        if not np.isfinite(cfo_ppm):
            cfo_ppm = 0.0

        # Histogramme de phase différentielle (4 quadrants).
        if self.constellation_domain == "differential":
            dph_src = p
        else:
            if p.size < 2:
                dph_src = np.zeros(0, dtype=np.complex64)
            else:
                dph_src = p[1:] * np.conj(p[:-1])
        if dph_src.size:
            m = np.abs(dph_src)
            med_m = float(np.median(m))
            if med_m > 1e-12:
                keep = m > (0.30 * med_m)
                if np.count_nonzero(keep) >= 16:
                    dph_src = dph_src[keep]
        ph_hist = self._phase_histogram_quadrants(np.angle(dph_src)) if dph_src.size else np.zeros(4, dtype=np.float32)

        ecc = self._qpsk_cluster_eccentricity(p) if mode == "qpsk" else 0.0
        return {
            "lock": lock,
            "state": state,
            "evm_pct": evm,
            "evm_rad_pct": evm_rad,
            "evm_tan_pct": evm_tan,
            "evm_rt_ratio": evm_rt_ratio,
            "mer_db": mer_db,
            "lock_metric": c_metric,
            "mode": mode,
            "domain": self.constellation_domain,
            "sps": sps,
            "sps_nom": sps_nom,
            "sps_off_ppm": sps_off_ppm,
            "iq_imbalance": float(np.abs(self._iq_rho)),
            "cfo_hz": cfo_hz,
            "cfo_ppm": cfo_ppm,
            "ted_mean": float(self._ted_mean),
            "ted_std": float(self._ted_std),
            "timing_corr": float(self._timing_corr_norm),
            "timing_clips": int(self._timing_clip_events),
            "phase_hist": [float(ph_hist[0]), float(ph_hist[1]), float(ph_hist[2]), float(ph_hist[3])],
            "cluster_ecc": ecc,
            "eq_on": bool(self._eq_enabled and self.modulation_profile == "tetra"),
            "eq_err": float(self._eq_err_rms),
            "eq_upd": float(self._eq_upd_norm),
            "costas_active": bool(self._costas_active_last),
        }

    def _maybe_emit_quality(self, points: np.ndarray, fs_for_sps: Optional[float] = None):
        now = time.monotonic()
        if (now - self._last_quality_emit) < self._quality_interval_s:
            return
        q = self._compute_quality(points, fs_for_sps)
        if q is None:
            return
        self._last_quality_emit = now
        self.quality_updated.emit(q)

    def _apply_costas_streaming(self, iq: np.ndarray) -> np.ndarray:
        if iq is None or iq.size == 0:
            return iq

        bw = max(1e-5, float(self.costas_loop_bw))
        zeta = max(0.1, float(self.costas_damping))
        den = 1.0 + 2.0 * zeta * bw + bw * bw
        alpha = (4.0 * zeta * bw) / den
        beta = (4.0 * bw * bw) / den

        phase = float(self._costas_phase)
        freq = float(self._costas_freq)
        out = np.empty_like(iq, dtype=np.complex64)

        mode = self.costas_mode

        for i, s in enumerate(iq):
            y = s * np.exp(-1j * phase)
            if mode == "bpsk":
                err = np.sign(np.real(y)) * np.imag(y)
            else:
                err = np.sign(np.real(y)) * np.imag(y) - np.sign(np.imag(y)) * np.real(y)

            freq += beta * err
            phase += freq + alpha * err

            if phase > np.pi:
                phase -= 2.0 * np.pi
            elif phase < -np.pi:
                phase += 2.0 * np.pi

            out[i] = y

        self._costas_phase = phase
        self._costas_freq = freq
        return out

    def _apply_symbol_equalizer(self, symbols: np.ndarray) -> np.ndarray:
        """
        Egaliseur aveugle CMA au rythme symbole pour réduire l'ISI (profil TETRA).
        """
        if symbols is None or symbols.size == 0:
            return np.zeros(0, dtype=np.complex64)
        # SAFE MODE: EQ adaptatif temporairement bypassé (instabilités observées).
        self._eq_err_rms *= 0.98
        self._eq_upd_norm *= 0.98
        return self._sanitize_complex(symbols, max_abs=20.0)

    def _extract_symbol_samples(self, bb: np.ndarray, fs_bb: float) -> np.ndarray:
        """
        Extrait des points au rythme symbole avec:
          - phase grossière (blind) pour l'accroche,
          - TED type Gardner pour stabiliser la synchro temporelle.
        """
        if bb is None or bb.size < 2 or fs_bb <= 0.0 or self.symbol_rate <= 0.0:
            return np.zeros(0, dtype=np.complex64)

        sps_nom = float(fs_bb) / float(self.symbol_rate)
        if sps_nom < 1.0:
            return np.zeros(0, dtype=np.complex64)
        # Asservissement lent de cadence symbole (corrige les dérives sur longues durées).
        # Limiter strictement l'asservissement de cadence (évite les dérives lentes internes).
        sps = float(np.clip(sps_nom + self._sps_offset, 0.995 * sps_nom, 1.005 * sps_nom))

        out = []
        n = int(bb.size)

        # Recherche grossière de phase symbole (accroche), avec hystérésis.
        phase = float(self._sym_phase % sps)
        self._timing_reacq_ctr = max(0, self._timing_reacq_ctr - 1)
        need_reacq = (self._timing_conf < 0.18) and (self._timing_reacq_ctr <= 0)
        if need_reacq and sps >= 1.2 and n >= 32:
            n_cand = int(min(32, max(8, round(sps * 4))))
            candidates = np.linspace(0.0, sps, n_cand, endpoint=False)
            best_metric = -1.0
            best_phase = phase
            pow_n = 2 if self.costas_mode == "bpsk" else 4
            for off in candidates:
                p = float(off)
                seq = []
                cnt = 0
                while p < (n - 1) and cnt < 96:
                    i0 = int(p)
                    frac = p - i0
                    y = (1.0 - frac) * bb[i0] + frac * bb[i0 + 1]
                    seq.append(y)
                    cnt += 1
                    p += sps
                if len(seq) >= 8:
                    arr = np.asarray(seq, dtype=np.complex64)
                    d = arr[1:] * np.conj(arr[:-1])
                    dn = d / (np.abs(d) + 1e-12)
                    metric = float(np.abs(np.mean(dn ** pow_n)))
                    if metric > best_metric:
                        best_metric = metric
                        best_phase = float(off)
            phase = 0.85 * phase + 0.15 * best_phase
            self._timing_reacq_ctr = 180

        ted_err = []
        while phase < (n - 1):
            y = self._interp_linear(bb, phase)
            out.append(y)

            # Erreur de timing Gardner (early/late à +/- T/2)
            t_e = phase - 0.5 * sps
            t_l = phase + 0.5 * sps
            if t_e >= 0.0 and t_l < (n - 1):
                y_e = self._interp_linear(bb, t_e)
                y_l = self._interp_linear(bb, t_l)
                e = np.real((y_l - y_e) * np.conj(y))
                e = float(np.clip(e, -2.0, 2.0))
                ted_err.append(e)
            phase += sps

        next_phase = phase - n
        if ted_err:
            e_arr = np.asarray(ted_err, dtype=np.float32)
            e_mean = float(np.mean(e_arr))
            e_std = float(np.std(e_arr))
            self._ted_mean = 0.90 * self._ted_mean + 0.10 * e_mean
            self._ted_std = 0.90 * self._ted_std + 0.10 * e_std

            max_corr = 0.01 * sps
            corr = float(np.clip(self._timing_gain * e_mean, -max_corr, max_corr))
            if abs(corr) >= 0.98 * max_corr:
                self._timing_clip_events += 1
            self._timing_corr_norm = 0.90 * self._timing_corr_norm + 0.10 * (corr / max(1e-9, sps))
            next_phase += corr
            # Boucle lente sur la cadence: persistance d'erreur timing => ajuster sps.
            if self._timing_conf > 0.35:
                self._sps_offset = float(
                    np.clip(
                        0.9995 * self._sps_offset + 0.002 * corr,
                        -0.005 * sps_nom,
                        0.005 * sps_nom,
                    )
                )
            else:
                self._sps_offset *= 0.9998
        else:
            self._ted_mean *= 0.98
            self._ted_std *= 0.98
            self._timing_corr_norm *= 0.98
            self._sps_offset *= 0.9998
        self._sym_phase = next_phase

        if not out:
            return np.zeros(0, dtype=np.complex64)
        arr = self._sanitize_complex(np.asarray(out, dtype=np.complex64), max_abs=20.0)

        # Confiance timing: cohérence différentielle locale.
        if arr.size >= 12:
            d = arr[1:] * np.conj(arr[:-1])
            dn = d / (np.abs(d) + 1e-12)
            pow_n = 2 if self.costas_mode == "bpsk" else 4
            conf = float(np.abs(np.mean(dn ** pow_n)))
            self._timing_conf = 0.92 * self._timing_conf + 0.08 * conf
            if conf < 0.14:
                self._timing_reacq_ctr = 0
                self._sps_offset *= 0.90
            elif conf > 0.35:
                self._timing_reacq_ctr = max(self._timing_reacq_ctr, 24)

        return arr

    def _map_constellation_domain(self, points: np.ndarray) -> np.ndarray:
        if points is None or points.size == 0:
            return np.zeros(0, dtype=np.complex64)

        p = self._sanitize_complex(points, max_abs=20.0)
        if self.constellation_domain != "differential":
            return p

        if self._prev_const_sample is not None:
            p = np.concatenate((np.asarray([self._prev_const_sample], dtype=np.complex64), p))

        if p.size < 2:
            self._prev_const_sample = np.complex64(p[-1])
            return np.zeros(0, dtype=np.complex64)

        d = p[1:] * np.conj(p[:-1])
        d = self._sanitize_complex(d, max_abs=20.0)
        self._prev_const_sample = np.complex64(p[-1])
        if d.size == 0:
            return np.zeros(0, dtype=np.complex64)

        # Écarter les points de très faible magnitude (phase peu fiable en différentiel).
        mag = np.abs(d)
        med = float(np.median(mag)) if mag.size else 0.0
        thr = max(1e-9, 0.35 * med)
        keep = mag > thr
        if np.any(keep):
            d = d[keep]
        if d.size == 0:
            return np.zeros(0, dtype=np.complex64)

        # Normalisation globale (pas point-par-point) pour l'affichage.
        rms = float(np.sqrt(np.mean(np.abs(d) ** 2)))
        if np.isfinite(rms) and rms > 1e-12:
            d = d / rms
        else:
            return np.zeros(0, dtype=np.complex64)
        return d.astype(np.complex64, copy=False)

    # --------------- (Re)config DSP sous-bande ---------------
    def _apply_bw_params(self):
        """
        Recalcule:
          - la décimation entière input->bb
          - le FIR sous-bande
          - la détection (NFM/WFM) et notifie le démod
          - le fs_bb poussé au démod
        """
        fs = float(self.sample_rate)

        # 1) Décider NFM/WFM (auto si pas de bouton)
        if self.modulation_profile == "tetra":
            is_wide = False
        else:
            try:
                is_wide = (getattr(self.demod, "mode", None) and "WIDE" in str(self.demod.mode)) or (
                    self._bandwidth >= 120e3
                )
            except Exception:
                is_wide = (self._bandwidth >= 120e3)

        # 2) Choisir d et k pour approcher fs_bb = 48k * k
        def best_d_and_k(fs_hz: float, want_wide: bool):
            if self.modulation_profile == "tetra":
                target_list = [72_000.0]
            else:
                k_list = [1] if not want_wide else [4, 5, 6]
                target_list = [48_000.0 * k for k in k_list]
            best = None
            for target in target_list:
                d = int(max(1, round(fs_hz / target)))
                fs_bb = fs_hz / d
                rel_err = abs(fs_bb - target) / target
                k = max(1, int(round(fs_bb / 48_000.0)))
                if best is None or rel_err < best[0]:
                    best = (rel_err, d, k, fs_bb, target)
            return best  # (err, d, k, fs_bb, target)

        # Pré-décimation coarse pour garder le FIR principal dans une zone CPU tenable.
        pre_decim = 1
        if fs >= 7_000_000.0:
            pre_decim = 4
        elif fs >= 3_500_000.0:
            pre_decim = 2
        fs_stage = fs / float(pre_decim)

        err, d, k, fs_bb, target = best_d_and_k(fs_stage, is_wide)

        if err > 0.003:
            if self.modulation_profile == "tetra":
                target_bb = 72_000.0
            else:
                target_bb = 192_000.0 if is_wide else 48_000.0
            d = int(max(1, round(fs_stage / max(1.0, target_bb))))
            fs_bb = fs_stage / d
            k = max(1, int(round(fs_bb / 48_000.0)))
            target = target_bb if self.modulation_profile == "tetra" else (48_000.0 * k)
            err = abs(fs_bb - target) / target

        self._pre_decim = int(max(1, pre_decim))
        self._pre_residual = np.zeros(0, dtype=np.complex64)
        self._decim = d
        self._fs_bb = fs_bb  # ≈ 48k*k

        # 3) FIR sous-bande (anti-alias & shape)
        if self.modulation_profile == "tetra":
            occ = 0.5 * self.symbol_rate * (1.0 + self._rrc_rolloff)
            cutoff_bw = min(0.48 * self._bandwidth, 1.08 * occ)
        else:
            cutoff_bw = 0.45 * self._bandwidth
        cutoff_fsbb = 0.45 * self._fs_bb * 0.95
        cutoff = max(200.0, min(cutoff_bw, cutoff_fsbb))

        fir_taps = int(self.num_taps)
        if fs >= 7_000_000.0:
            fir_taps = min(fir_taps, 127)
        elif fs >= 3_500_000.0:
            fir_taps = min(fir_taps, 191)
        if (fir_taps % 2) == 0:
            fir_taps += 1

        self._taps_cache = design_lpf_fir(cutoff, fs_stage, num_taps=fir_taps, window="hamming")
        self._taps_bw, self._taps_fs = cutoff, fs_stage
        self._fir_zi = np.zeros(max(0, len(self._taps_cache) - 1), dtype=np.complex64)
        self._mix_phase = 0.0
        self._decim_phase = 0
        self._sym_phase = 0.0
        self._iq_rho = 0.0 + 0.0j
        self._last_quality_emit = 0.0
        self._rrc_taps = None
        self._rrc_zi = None
        self._tetra_rs_i = None
        self._tetra_rs_q = None
        self._tetra_rs_in = 0.0
        self._tetra_rs_out = 0.0
        self._reset_costas_state()
        self._reset_constellation_state()

        _log_rx(
            f"{self.name}: fs={fs:.1f} Hz, BW={self._bandwidth/1e3:.1f} kHz, "
            f"mode={'WFM' if is_wide else 'NFM'}, pre_d={self._pre_decim}, d={d}, k={k}, "
            f"fs_bb≈{fs_bb:.1f} (target={target:.1f}, err={err*100:.2f}%), "
            f"LPF_cut={cutoff:.1f} Hz, taps={fir_taps}"
        )

        # 4) Notifier le démod (mode + nouveau fs d'entrée)
        if self.demod is not None:
            try:
                if hasattr(self.demod, "set_mode"):
                    from src.core.demodulators.fm import FMAudioMode  # évite import cycle
                    desired = FMAudioMode.WIDE if is_wide else FMAudioMode.NARROW
                    if getattr(self.demod, "_mode", None) != desired:
                        if hasattr(self.demod, "begin_reconfig"):
                            self.demod.begin_reconfig(mute_sec=0.15)
                        self.demod.set_mode(desired)

                self.demod.set_input_rate(self._fs_bb)
            except Exception as e:
                _log_rx(f"{self.name}: notify demod error: {e!r}")

        # fin de reconfig éventuellement déclenchée par set_bandwidth()
        self._reconfig.clear()

    def _apply_pre_decim_streaming(self, x: np.ndarray) -> np.ndarray:
        p = int(max(1, self._pre_decim))
        if x is None or x.size == 0:
            return np.zeros(0, dtype=np.complex64)
        if p <= 1:
            return x.astype(np.complex64, copy=False)

        if self._pre_residual is not None and self._pre_residual.size:
            x = np.concatenate((self._pre_residual, x))

        n_full = (int(x.size) // p) * p
        if n_full <= 0:
            self._pre_residual = x.astype(np.complex64, copy=True)
            return np.zeros(0, dtype=np.complex64)

        x_full = x[:n_full]
        self._pre_residual = x[n_full:].astype(np.complex64, copy=True)

        y = x_full.reshape(-1, p).mean(axis=1)
        return y.astype(np.complex64, copy=False)

    # --------------------- Traitement ---------------------
    @pyqtSlot(np.ndarray)
    def process_block(self, iq_block: np.ndarray):
        try:
            self._process_block_impl(iq_block)
        except Exception:
            LOGGER.exception("%s: unhandled error in process_block", self.name)

    def _process_block_impl(self, iq_block: np.ndarray):
        """
        Appelé par la boucle SDR (flux IQ au taux self.sample_rate).
        Produit bb à fs_bb et l'envoie au démod (s'il est démarré).
        """
        if self._reconfig.is_set() or (not self._running):
            return
        if iq_block is None or iq_block.size < 2:
            return

        started_at = time.perf_counter()
        baseband_samples = 0
        demod_time_s = 0.0

        try:
            fs = self.sample_rate
            # offset: fréquence sélectionnée vs centre SDR
            try:
                fc = float(self._center_freq_provider())
            except Exception:
                fc = 0.0
            f_off = float(self._selected_freq - fc)

            # 1) translation en bande de base avec phase continue entre blocs
            if abs(f_off) < 1e-12 or fs <= 0:
                bb = iq_block
            else:
                bb, self._mix_phase = mix_to_baseband_block(
                    iq_block,
                    frequency_offset_hz=f_off,
                    sample_rate_hz=fs,
                    initial_phase=self._mix_phase,
                )

            # 1b) pré-décimation coarse pour limiter la charge CPU aux fortes FS.
            bb = self._apply_pre_decim_streaming(bb)
            if bb.size < 2:
                return

            # 2) filtrage sous-bande avec état FIR conservé entre blocs
            taps = self._taps_cache
            if taps is not None:
                zi = self._fir_zi
                if zi is None or zi.size != max(0, len(taps) - 1):
                    zi = np.zeros(max(0, len(taps) - 1), dtype=np.complex64)
                bb, self._fir_zi = lfilter(taps, [1.0], bb, zi=zi)

            # 3) décimation entière en mode streaming (phase conservée entre blocs)
            d = int(self._decim) if self._decim else 1
            if d > 1:
                bb, self._decim_phase = streaming_decimate(bb, d, self._decim_phase)
            fs_bb = self._fs_bb

            # 3b) correction IQ logicielle (déséquilibre gain/phase + DC)
            bb = self._apply_iq_correction(bb)
            if bb.size < 2:
                return

            # 3c) filtre adapté (RRC) pour profil numérique (ex: TETRA)
            if self.modulation_profile == "tetra":
                bb, fs_bb = self._apply_tetra_symbol_resample(bb, fs_bb)
                if bb.size < 2:
                    return
                bb = self._apply_rrc_streaming(bb)
                if bb.size < 2:
                    return

            # 4) (optionnel) boucle de Costas
            use_costas = bool(self.enable_costas)
            if self.modulation_profile == "tetra" and self.constellation_domain == "differential":
                # En affichage différentiel, Costas apporte peu et peut injecter du jitter.
                use_costas = False
            self._costas_active_last = use_costas
            if use_costas:
                bb = self._apply_costas_streaming(bb)

            baseband_samples = int(bb.size)

            # 5) envoi vers le démod (asynchrone audio; NE PAS bloquer)
            if self.demod is not None and getattr(self.demod, "_running", False):
                try:
                    demod_started_at = time.perf_counter()
                    self.demod.process_block(bb, fs_bb)
                    demod_time_s = time.perf_counter() - demod_started_at
                except Exception as e:
                    _log_rx(f"{self.name}: demod.process_block error: {e!r}")

            # 6) sortie IQ post-traitement (affichages, enregistrements, etc.)
            try:
                if self.constellation_mode == "symbols":
                    points = self._extract_symbol_samples(bb, fs_bb)
                    points = self._apply_symbol_equalizer(points)
                    points = self._map_constellation_domain(points)
                    if points.size:
                        self._maybe_emit_quality(points, fs_bb)
                        self.iq_out.emit(points)
                else:
                    points = self._map_constellation_domain(bb)
                    if points.size:
                        self._maybe_emit_quality(points, fs_bb)
                        self.iq_out.emit(points)
            except Exception:
                pass
        finally:
            self._record_perf(
                int(iq_block.size),
                baseband_samples,
                time.perf_counter() - started_at,
                demod_time_s,
            )
