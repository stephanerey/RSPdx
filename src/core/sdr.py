import logging
import threading
import time

import numpy as np
import SoapySDR
from PyQt5 import QtCore
from PyQt5.QtCore import QObject, pyqtSignal
from SoapySDR import SOAPY_SDR_CF32, SOAPY_SDR_RX

from src.config.settings import (
    DEFAULT_BUFF_SIZE,
    DEFAULT_CENTER_FREQ,
    DEFAULT_FFT_FPS,
    DEFAULT_IF_GAIN,
    DEFAULT_PERF_LOG_INTERVAL_S,
    DEFAULT_RF_GAIN,
    DEFAULT_SAMPLE_RATE,
    MAX_HISTORY_SIZE,
)
from src.core.data_storage import DataStorage
from src.core.dsp import apply_ema, blackman_window, compute_power_spectrum_db, fft_max_for_sample_rate, frequency_axis, select_fft_size


class SDRController(QObject):
    iq_block = pyqtSignal(np.ndarray)
    new_iq_data = pyqtSignal(np.ndarray)     # flux IQ brut (si besoin)
    new_data    = pyqtSignal(np.ndarray)     # pour la constellation (IQ)
    center_frequency_changed = QtCore.pyqtSignal(float)
    sample_rate_about_to_change = QtCore.pyqtSignal(float)  # nouveau FS
    sample_rate_changed = QtCore.pyqtSignal(float)
    perf_updated = QtCore.pyqtSignal(dict)

    def __init__(
        self,
        sample_rate=DEFAULT_SAMPLE_RATE,
        center_freq=DEFAULT_CENTER_FREQ,
        buff_size=DEFAULT_BUFF_SIZE,
        thread_manager=None,
    ):
        super().__init__()
        self.logger = logging.getLogger("RSPdx.SDRController")

        # État
        self.thread_manager = thread_manager
        self.running = False
        self._thread_name = "sdr_controller"
        self.thread = None
        self.stream = None
        self._last_stream_error_log = 0.0
        self._timeout_code = int(getattr(SoapySDR, "SOAPY_SDR_TIMEOUT", -1))
        self._last_plot_push = 0.0
        self._plot_interval_s = 1.0 / float(DEFAULT_FFT_FPS)
        self._fft_db_ema = None
        self._fft_ema_alpha = 1.0
        self._fft_win = None
        self._fft_win_size = 0
        self._fft_win_power = 1.0
        self._freq_axis = None
        self._freq_axis_key = None
        self._perf_log_interval_s = float(DEFAULT_PERF_LOG_INTERVAL_S)
        self._perf_window_started_at = time.monotonic()
        self._perf_last_log_at = self._perf_window_started_at
        self._perf_blocks = 0
        self._perf_samples = 0
        self._perf_fft_updates = 0
        self._perf_fft_time_s = 0.0
        self._perf_timeouts = 0
        self._perf_stream_errors = 0

        # Réglages
        self.sample_rate = float(sample_rate)
        self.center_freq = float(center_freq)
        self.buff_size   = int(buff_size)
        # FFT d'affichage: taille adaptative pour meilleure résolution fréquentielle.
        self.fft_size = select_fft_size(self.sample_rate, self.buff_size)

        # Matériel / infos
        self.sdr = None
        self.hwinfo = {}

        # Data storage (spectre, etc.)
        self.data_storage = DataStorage(max_history_size=MAX_HISTORY_SIZE)

        # Découverte et ouverture SDR (robuste)
        self._init_device()

        # Gains par défaut
        self.if_gain = DEFAULT_IF_GAIN
        self.rf_gain = DEFAULT_RF_GAIN
        self.agc     = False

        # Appliquer la config si HW présent
        if self.sdr is not None:
            self.sdr.setSampleRate(SOAPY_SDR_RX, 0, self.sample_rate)
            self.sdr.setFrequency(SOAPY_SDR_RX, 0, self.center_freq)

    # ---- Device init (robuste) ----
    def _init_device(self):
        # Infos modules Soapy (diagnostic utile en cas de non-détection).
        self.hwinfo["modules"] = []
        try:
            lm = getattr(SoapySDR, "listModules", None)
            if callable(lm):
                mods = lm()
                if isinstance(mods, (list, tuple)):
                    self.hwinfo["modules"] = [str(m) for m in mods]
        except Exception:
            self.hwinfo["modules"] = []

        # Enumerate all devices first (robuste aux variations de drivers Soapy).
        try:
            devices = SoapySDR.Device_enumerate()
        except Exception as e:
            devices = []
            self.logger.warning("Soapy enumerate failed: %s", e)
        # Essais d'énumération ciblés SDRplay si l'énumération globale est vide.
        if not devices:
            for args in (dict(driver="sdrplay"), dict(driver="sdrplay_api")):
                try:
                    d2 = SoapySDR.Device_enumerate(args)
                    if d2:
                        devices = d2
                        break
                except Exception:
                    pass
        self.hwinfo['devices'] = devices

        def _looks_like_sdrplay(dev) -> bool:
            if not isinstance(dev, dict):
                return False
            txt = " ".join(str(v).lower() for v in dev.values())
            return ("sdrplay" in txt) or ("rsp" in txt)

        opened = None
        open_errs = []

        # 1) Ouvrir directement un device trouvé à l'énumération.
        for dev in devices:
            if not _looks_like_sdrplay(dev):
                continue
            try:
                opened = SoapySDR.Device(dev)
                self.hwinfo["selected_device"] = dict(dev)
                break
            except Exception as e:
                open_errs.append(f"enum-open {dev}: {e}")

        # 2) Fallbacks par driver key (selon install Soapy/SDRplay).
        if opened is None:
            for args in (dict(driver="sdrplay"), dict(driver="sdrplay_api")):
                try:
                    opened = SoapySDR.Device(args)
                    self.hwinfo["selected_device"] = dict(args)
                    break
                except Exception as e:
                    open_errs.append(f"driver-open {args}: {e}")

        # 3) Dernier fallback: device par défaut.
        if opened is None:
            try:
                opened = SoapySDR.Device()
                info = opened.getHardwareInfo() if hasattr(opened, "getHardwareInfo") else {}
                if isinstance(info, dict):
                    txt = " ".join(str(v).lower() for v in info.values())
                    if ("sdrplay" in txt) or ("rsp" in txt):
                        self.hwinfo["selected_device"] = dict(info)
                    else:
                        # Device par défaut non-SDRplay: ne pas l'utiliser.
                        opened = None
            except Exception as e:
                open_errs.append(f"default-open: {e}")

        self.sdr = opened
        if self.sdr is None:
            self.logger.warning("No SDRPlay device opened; running in dummy mode.")
            if open_errs:
                self.logger.warning("SDRPlay open attempts:")
                for msg in open_errs[:8]:
                    self.logger.warning("  - %s", msg)
            mods = [m.lower() for m in self.hwinfo.get("modules", [])]
            if mods and (not any("sdrplay" in m for m in mods)):
                self.logger.warning("Soapy module list does not contain SDRplay. Installed modules:")
                for m in self.hwinfo.get("modules", [])[:20]:
                    self.logger.warning("  - %s", m)

        if self.sdr is not None:
            # Infos réelles
            try:
                self.hwinfo['antennas'] = self.sdr.listAntennas(SOAPY_SDR_RX, 0)
            except Exception:
                self.hwinfo['antennas'] = ["Antenna A", "Antenna B"]
            try:
                self.hwinfo['gainRange'] = self.sdr.getGainRange(SOAPY_SDR_RX, 0)
            except Exception:
                self.hwinfo['gainRange'] = None
            try:
                srs = self.sdr.listSampleRates(SOAPY_SDR_RX, 0)
                self.hwinfo['sampleRates'] = srs if srs else [self.sample_rate]
            except Exception:
                self.hwinfo['sampleRates'] = [self.sample_rate]
        else:
            # Valeurs par défaut en dummy
            self.hwinfo['antennas']    = ["Antenna A", "Antenna B"]
            self.hwinfo['gainRange']   = None
            self.hwinfo['sampleRates'] = [self.sample_rate]

    def update_fft_for_view(self, visible_span_hz: float, pixel_width: int):
        fs = float(max(1.0, self.sample_rate))
        span = float(max(1.0, min(abs(visible_span_hz), fs)))
        width_px = int(max(128, pixel_width))

        base_fft = select_fft_size(fs, self.buff_size)
        max_fft = fft_max_for_sample_rate(fs, self.buff_size)

        # Sur-échantillonnage d'affichage: plusieurs bins FFT pour un pixel visible.
        zoom_target = fs * float(width_px) * 6.0 / span
        zoom_fft = int(2 ** np.ceil(np.log2(max(1024.0, zoom_target))))
        desired = int(min(max_fft, max(base_fft, zoom_fft)))

        if desired == int(self.fft_size):
            return

        self.fft_size = desired
        self._fft_win = None
        self._fft_win_size = 0
        self._fft_win_power = 1.0
        self._fft_db_ema = None
        self._freq_axis = None
        self._freq_axis_key = None

    # ---- Cycle de vie ----
    def start(self):
        if self.running:
            return
        self.running = True
        self._reset_perf_counters()
        self.thread = threading.Thread(target=self.run, daemon=True, name="SDR-Thread")
        self.thread.start()
        if self.thread_manager is not None:
            self.thread_manager.register_external_thread(self._thread_name, self.thread)

    def stop(self):
        self.running = False
        if self.sdr is not None and self.stream is not None:
            try:
                self.sdr.deactivateStream(self.stream)
            except Exception:
                pass
            try:
                self.sdr.closeStream(self.stream)
            except Exception:
                pass
            self.stream = None
        if self.thread and self.thread.is_alive():
            if threading.current_thread() is not self.thread:
                try:
                    self.thread.join(timeout=2.0)
                except RuntimeError:
                    pass
        if self.thread_manager is not None:
            self.thread_manager.unregister_external_thread(self._thread_name)
        self.thread = None

    # ---- Boucle d’acquisition ----
    def run(self):
        try:
            if self.sdr is None:
                # ----- DUMMY MODE: génère IQ + spectre -----
                t = 0
                buffer = np.zeros(self.buff_size, dtype=np.complex64)
                while self.running:
                    n  = np.arange(self.buff_size, dtype=np.float32)
                    fs = float(self.sample_rate)
                    # deux tons + bruit
                    tone1 = np.exp(1j * 2*np.pi*(0.10*fs)*n/fs)
                    tone2 = np.exp(1j * 2*np.pi*(0.22*fs)*n/fs)
                    noise = 0.1 * (np.random.randn(self.buff_size) + 1j*np.random.randn(self.buff_size))
                    buffer = (0.5*tone1 + 0.3*tone2 + noise).astype(np.complex64)

                    self.iq_block.emit(buffer.copy())
                    self._record_perf_block(buffer.size)
                    now = time.monotonic()
                    if now - self._last_plot_push >= self._plot_interval_s:
                        try:
                            fft_t0 = time.monotonic()
                            power = self.compute_spectrum(buffer)
                            self._perf_fft_time_s += max(0.0, time.monotonic() - fft_t0)
                            self._perf_fft_updates += 1
                            freqs = self._get_freq_axis(len(power), fs)
                            self.data_storage.update({"timestamp": t, "x": freqs, "y": power})
                        except Exception as e:
                            now_err = time.monotonic()
                            if now_err - self._last_stream_error_log >= 1.0:
                                self.logger.warning("Spectrum compute error (dummy): %s", e)
                                self._last_stream_error_log = now_err
                        self._last_plot_push = now
                    self._maybe_log_perf(now, mode="dummy")

                    t += 1
                    time.sleep(0.01)
                return

            # ----- HARDWARE PATH -----
            self.sdr.setSampleRate(SOAPY_SDR_RX, 0, self.sample_rate)
            self.sdr.setFrequency(SOAPY_SDR_RX, 0, self.center_freq)
            self.sdr.setGainMode(SOAPY_SDR_RX, 0, False)
            self.sdr.setGain(SOAPY_SDR_RX, 0, 'IFGR', self.if_gain)
            self.sdr.setGain(SOAPY_SDR_RX, 0, 'RFGR', self.rf_gain)

            if self.stream is None:
                self.stream = self.sdr.setupStream(SOAPY_SDR_RX, SOAPY_SDR_CF32)
            # IMPORTANT: flags=0 pour lever toute ambiguïté d’overload
            self.sdr.activateStream(self.stream, 0)
            self.logger.info("Hardware stream activated: fs=%s, fc=%s", self.sample_rate, self.center_freq)

            buffer = np.zeros(self.buff_size, dtype=np.complex64)
            while self.running:
                sr = self.sdr.readStream(self.stream, [buffer], self.buff_size)
                if sr.ret > 0:
                    n_read = int(sr.ret)
                    iq = buffer[:n_read].copy()
                    self.iq_block.emit(iq)
                    self._record_perf_block(n_read)
                    now = time.monotonic()
                    if now - self._last_plot_push >= self._plot_interval_s:
                        try:
                            fft_t0 = time.monotonic()
                            power = self.compute_spectrum(iq)
                            self._perf_fft_time_s += max(0.0, time.monotonic() - fft_t0)
                            self._perf_fft_updates += 1
                            fs = float(self.sample_rate)
                            freqs = self._get_freq_axis(len(power), fs)
                            self.data_storage.update({"timestamp": now, "x": freqs, "y": power})
                        except Exception as e:
                            now_err = time.monotonic()
                            if now_err - self._last_stream_error_log >= 1.0:
                                self.logger.warning("Spectrum compute error (hardware): %s", e)
                                self._last_stream_error_log = now_err
                        self._last_plot_push = now
                    self._maybe_log_perf(now, mode="hardware")
                elif sr.ret == self._timeout_code:
                    self._perf_timeouts += 1
                    time.sleep(0.001)
                elif sr.ret < 0:
                    self._perf_stream_errors += 1
                    # Limiter les logs d'erreur stream pour éviter le spam.
                    now = time.monotonic()
                    if now - self._last_stream_error_log >= 1.0:
                        self.logger.warning("readStream error: ret=%s", sr.ret)
                        self._last_stream_error_log = now
                    time.sleep(0.001)

        except Exception as e:
            self.logger.exception("SDR runtime error: %s", e)
        finally:
            # Fermeture propre du stream matériel
            if self.sdr is not None and self.stream is not None:
                try:
                    self.sdr.deactivateStream(self.stream)
                except Exception:
                    pass
                try:
                    self.sdr.closeStream(self.stream)
                except Exception:
                    pass
                self.stream = None
            if self.thread_manager is not None:
                self.thread_manager.unregister_external_thread(self._thread_name)

    def _reset_perf_counters(self) -> None:
        now = time.monotonic()
        self._perf_window_started_at = now
        self._perf_last_log_at = now
        self._perf_blocks = 0
        self._perf_samples = 0
        self._perf_fft_updates = 0
        self._perf_fft_time_s = 0.0
        self._perf_timeouts = 0
        self._perf_stream_errors = 0

    @QtCore.pyqtSlot()
    def reset_perf_stats(self) -> None:
        self._reset_perf_counters()

    def _record_perf_block(self, sample_count: int) -> None:
        self._perf_blocks += 1
        self._perf_samples += int(sample_count)

    def _maybe_log_perf(self, now: float, mode: str) -> None:
        elapsed = now - self._perf_last_log_at
        if elapsed < self._perf_log_interval_s:
            return
        sample_rate_eff = self._perf_samples / max(elapsed, 1e-9)
        iq_mbit_s = sample_rate_eff * 64.0 / 1_000_000.0
        block_rate = self._perf_blocks / max(elapsed, 1e-9)
        fft_rate = self._perf_fft_updates / max(elapsed, 1e-9)
        fft_avg_ms = 1000.0 * self._perf_fft_time_s / max(1, self._perf_fft_updates)
        fs_target = float(max(1.0, self.sample_rate))
        fs_ratio = 100.0 * sample_rate_eff / fs_target
        perf_snapshot = {
            "mode": mode,
            "sample_rate_target_hz": fs_target,
            "sample_rate_effective_hz": sample_rate_eff,
            "sample_rate_ratio_pct": fs_ratio,
            "iq_mbit_s": iq_mbit_s,
            "block_rate_hz": block_rate,
            "fft_rate_hz": fft_rate,
            "fft_avg_ms": fft_avg_ms,
            "time_outs": int(self._perf_timeouts),
            "stream_errors": int(self._perf_stream_errors),
            "fft_size": int(self.fft_size),
            "buffer_size": int(self.buff_size),
        }
        self.perf_updated.emit(perf_snapshot)
        self._perf_last_log_at = now
        self._perf_blocks = 0
        self._perf_samples = 0
        self._perf_fft_updates = 0
        self._perf_fft_time_s = 0.0
        self._perf_timeouts = 0
        self._perf_stream_errors = 0

    # ---- Réglages ----
    def update_if_gain(self, value):
        self.if_gain = int(value)
        if self.sdr is not None:
            self.sdr.setGain(SOAPY_SDR_RX, 0, "IFGR", self.if_gain)

    def update_rf_gain(self, value):
        self.rf_gain = int(value)
        if self.sdr is not None:
            self.sdr.setGain(SOAPY_SDR_RX, 0, "RFGR", self.rf_gain)

    def update_agc(self, agc):
        self.agc = bool(agc)
        if self.sdr is not None:
            self.sdr.setGainMode(SOAPY_SDR_RX, 0, self.agc)

    def set_frequency(self, frequency):
        self.center_freq = float(frequency)
        self._freq_axis = None
        self._freq_axis_key = None
        if self.sdr is not None:
            self.sdr.setFrequency(SOAPY_SDR_RX, 0, self.center_freq)
        self.center_frequency_changed.emit(self.center_freq)

    def set_sample_rate(self, new_sample_rate):
        new_sample_rate = float(new_sample_rate)
        self.logger.info("Sample rate change requested: %s -> %s", self.sample_rate, new_sample_rate)
        was_running = bool(self.running)

        # 1) prévenir tout le monde (RX/démod) AVANT d'arrêter le flux
        self.sample_rate_about_to_change.emit(new_sample_rate)

        # 2) stop acquisition (coupe net l’émission de blocs IQ)
        #    Attention à ne pas join sur soi-même si appelé depuis le thread SDR.
        if was_running and threading.current_thread() is self.thread:
            # on signale à la boucle de sortir; le restart se fera depuis le thread appelant
            self.running = False
        elif was_running:
            self.stop()

        # 3) appliquer côté HW
        self.sample_rate = new_sample_rate
        self.fft_size = select_fft_size(self.sample_rate, self.buff_size)
        self._freq_axis = None
        self._freq_axis_key = None
        if self.sdr is not None:
            try:
                self.sdr.setSampleRate(SOAPY_SDR_RX, 0, self.sample_rate)
            except Exception as e:
                self.logger.warning("setSampleRate error: %s", e)

        # 4) signal “FS changé” (UI/Receiver)
        self.sample_rate_changed.emit(self.sample_rate)
        self.logger.info("Sample rate applied and signal emitted: %s", self.sample_rate)

        # 5) redémarrer proprement (si l'appel ne vient pas de la boucle SDR)
        if was_running and threading.current_thread() is not self.thread:
            self.start()

    def set_antenna(self, antenna):
        if not antenna:
            return
        self.antenna = antenna
        if self.sdr is not None:
            self.sdr.setAntenna(SOAPY_SDR_RX, 0, self.antenna)

    # ---- Spectre ----
    def _ensure_fft_window(self):
        n = int(max(8, self.fft_size))
        if self._fft_win is not None and self._fft_win_size == n:
            return
        w = blackman_window(n)
        pw = float(np.sum(w * w))
        if pw <= 1e-12:
            pw = 1.0
        self._fft_win = w
        self._fft_win_size = n
        self._fft_win_power = pw
        self._fft_db_ema = None
        self._freq_axis = None
        self._freq_axis_key = None

    def _get_freq_axis(self, n_bins: int, fs: float) -> np.ndarray:
        key = (int(n_bins), float(fs), float(self.center_freq))
        if self._freq_axis is not None and self._freq_axis_key == key:
            return self._freq_axis
        freqs = frequency_axis(int(n_bins), fs, self.center_freq)
        self._freq_axis = freqs
        self._freq_axis_key = key
        return freqs

    def compute_spectrum(self, iq_data):
        nfft = int(max(8, self.fft_size))
        self._ensure_fft_window()
        p_db = compute_power_spectrum_db(iq_data, nfft, window=self._fft_win, window_power=self._fft_win_power)
        self._fft_db_ema = apply_ema(p_db, self._fft_db_ema, alpha=self._fft_ema_alpha)
        return self._fft_db_ema.astype(np.float32, copy=False)
