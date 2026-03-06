from __future__ import annotations
import threading, datetime, time
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Tuple
import numpy as np
import sounddevice as sd

# NEW: on utilise le resampler dédié
from src.core.dsp.resampler import RationalResampler

# ---------- logs ----------
DEBUG_FM = False

def _log_fm(*args):
    if not DEBUG_FM: return
    ts = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
    th = threading.current_thread().name
    print(f"[FM][{ts}][{th}]", *args)

class FMAudioMode(Enum):
    NARROW = "nfm"
    WIDE   = "wfm"


@dataclass
class _DeemphState:
    a: float = 0.0
    b: float = 1.0
    z: float = 0.0

def _design_deemphasis(fs_audio: float, tau_sec: float) -> _DeemphState:
    dt = 1.0 / float(fs_audio)
    a = dt / (tau_sec + dt) if tau_sec > 0 else 1.0
    return _DeemphState(a=float(a), b=float(1.0 - a), z=0.0)

def _apply_deemphasis(x: np.ndarray, st: _DeemphState) -> np.ndarray:
    if x.size == 0: return x
    y = np.empty_like(x, dtype=np.float32)
    z, a, b = float(st.z), float(st.a), float(st.b)
    for i in range(x.size):
        z = a * float(x[i]) + b * z
        y[i] = z
    st.z = z
    return y

def _fm_phase_discriminator(bb: np.ndarray) -> np.ndarray:
    if bb.size < 2:
        return np.zeros(0, dtype=np.float32)
    x = bb.astype(np.complex64, copy=False)
    y = x[1:] * np.conj(x[:-1])
    return np.angle(y).astype(np.float32)

@dataclass
class _OnePoleLPF:
    a: float = 1.0
    z: float = 0.0

def _design_one_pole_lpf(fs: float, fc: float) -> _OnePoleLPF:
    if fc<=0 or fs<=0: return _OnePoleLPF(a=1.0, z=0.0)
    a = 1.0 - float(np.exp(-2.0*np.pi*fc/fs))
    return _OnePoleLPF(a=a, z=0.0)

def _apply_one_pole_lpf(x: np.ndarray, st: _OnePoleLPF) -> np.ndarray:
    if x.size==0: return x
    y = np.empty_like(x, dtype=np.float32)
    z, a = float(st.z), float(st.a)
    for i in range(x.size):
        z += a * (float(x[i]) - z); y[i] = z
    st.z = z; return y

# =========================================================
#                      FM DEMOD
# =========================================================
class FMDemodulator:
    def __init__(self, audio_rate: float = 48_000.0, deemph_us: float = 50.0,
                 mode: FMAudioMode = FMAudioMode.NARROW, audio_device: Optional[int] = None,
                 limiter: bool = True, deemph_enable: bool = True):
        self._audio_rate = float(audio_rate)
        self._in_rate    = float(48_000.0)   # sera mis à jour par set_input_rate()
        self._mode       = mode

        if deemph_us is None:
            deemph_us = 50.0 if mode == FMAudioMode.WIDE else 300.0
        self._deemph_enable = bool(deemph_enable)
        self._deemph = _design_deemphasis(self._audio_rate, float(deemph_us)*1e-6)
        fc = 8000.0 if mode == FMAudioMode.NARROW else 18000.0
        self._audio_lpf = _design_one_pole_lpf(self._audio_rate, fc)

        self._limiter = bool(limiter)
        self._gain = 1.5 if mode == FMAudioMode.NARROW else 0.35
        self._if_limiter = True
        self._audio_hp_enable = True
        self._audio_hp_fc = 250.0 if mode == FMAudioMode.NARROW else 40.0
        self._audio_hp_x1 = 0.0
        self._audio_hp_y1 = 0.0
        self._audio_hp_a = self._design_audio_hp(self._audio_rate, self._audio_hp_fc)

        # Audio sink
        self._stream: Optional[sd.OutputStream] = None
        self._device_index: Optional[int] = audio_device
        self._running = False

        # anti-click
        self._dc = 0.0
        self._dc_alpha = 0.001
        self._prev_bb: Optional[np.complex64] = None

        # mute/prefill/fade
        self._mute_until = 0.0
        self._prefill_needed = False
        self._prefill_target = int(self._audio_rate * 0.20)  # 200 ms
        self._fade_in_remaining = 0
        self._last_out = 0.0  # pour underrun

        # ring buffer (producteur: process_block, consommateur: callback)
        self._rb_size = int(self._audio_rate * 0.6)  # 600 ms
        self._rb = np.zeros(self._rb_size, dtype=np.float32)
        self._rb_w = 0; self._rb_r = 0
        self._rb_lock = threading.Lock()

        # NEW: resampler de sortie (bb -> audio_rate)
        self._out_rs: Optional[RationalResampler] = None

        # throttle logs
        self._last_log_t = 0.0

        _log_fm(f"INIT: audio_rate={self._audio_rate}, mode={self._mode}")

    # --- propriété lue par Receiver ---
    @property
    def mode(self) -> FMAudioMode:
        return self._mode

    def desired_input_rate(self, bw_hz: float) -> float:
        """fs souhaité en entrée du démod (après chaîne sous-bande)."""
        return 192_000.0 if (self._mode == FMAudioMode.WIDE or bw_hz >= 120e3) else 48_000.0

    # ---------- ring buffer helpers ----------
    def _rb_space(self) -> int:
        w, r, n = self._rb_w, self._rb_r, self._rb_size
        return (r - w - 1) % n

    def _rb_available(self) -> int:
        w, r, n = self._rb_w, self._rb_r, self._rb_size
        return (w - r) % n

    def _rb_write(self, x: np.ndarray):
        if x is None or x.size == 0: return
        x = x.astype(np.float32, copy=False)
        with self._rb_lock:
            space = self._rb_space(); n = min(space, x.size)
            if n <= 0: return
            n1 = min(n, self._rb_size - self._rb_w)
            self._rb[self._rb_w:self._rb_w+n1] = x[:n1]
            self._rb_w = (self._rb_w + n1) % self._rb_size
            n2 = n - n1
            if n2>0:
                self._rb[0:n2] = x[n1:n1+n2]
                self._rb_w = (self._rb_w + n2) % self._rb_size

    def _rb_read(self, n: int) -> np.ndarray:
        out = np.zeros(n, dtype=np.float32)
        with self._rb_lock:
            avail = self._rb_available(); m = min(avail, n)
            if m>0:
                n1 = min(m, self._rb_size - self._rb_r)
                out[:n1] = self._rb[self._rb_r:self._rb_r+n1]
                self._rb_r = (self._rb_r + n1) % self._rb_size
                n2 = m - n1
                if n2>0:
                    out[n1:n1+n2] = self._rb[0:n2]
                    self._rb_r = (self._rb_r + n2) % self._rb_size
        return out

    # ---------- dynamic params ----------
    def set_input_rate(self, fs_in: float) -> None:
        fs_in = float(fs_in)
        change = abs(fs_in - self._in_rate) / max(1.0, self._in_rate) > 0.005
        self._in_rate = fs_in
        # Tenir à jour le resampler uniquement en cas de vrai changement de ratio.
        if change and self._out_rs is not None:
            self._out_rs.set_ratio(self._in_rate, self._audio_rate)
        if change:
            self.begin_reconfig(mute_sec=0.20)
        _log_fm(f"set_input_rate(fs_in={self._in_rate:.1f}) for FM demod input")

    def set_audio_device(self, device_index: Optional[int]) -> None:
        self._device_index = device_index

    def set_mode(self, mode: FMAudioMode):
        _log_fm(f"set_mode: {getattr(self, '_mode', None)} -> {mode}")
        self._mode = mode
        self._gain = 1.5 if mode == FMAudioMode.NARROW else 0.35
        deemph_us = 300.0 if mode == FMAudioMode.NARROW else 50.0
        self._deemph = _design_deemphasis(self._audio_rate, deemph_us * 1e-6)
        fc = 3_000.0 if mode == FMAudioMode.NARROW else 15_000.0
        self._audio_lpf = _design_one_pole_lpf(self._audio_rate, fc)
        self._audio_hp_fc = 250.0 if mode == FMAudioMode.NARROW else 40.0
        self._audio_hp_a = self._design_audio_hp(self._audio_rate, self._audio_hp_fc)
        self._audio_hp_x1 = 0.0
        self._audio_hp_y1 = 0.0
        self.begin_reconfig(mute_sec=0.15)

    @staticmethod
    def _design_audio_hp(fs: float, fc: float) -> float:
        if fs <= 0.0 or fc <= 0.0:
            return 0.0
        rc = 1.0 / (2.0 * np.pi * fc)
        dt = 1.0 / fs
        return float(rc / (rc + dt))

    def _apply_audio_hp(self, x: np.ndarray) -> np.ndarray:
        if x is None or x.size == 0 or (not self._audio_hp_enable) or self._audio_hp_a <= 0.0:
            return x
        y = np.empty_like(x, dtype=np.float32)
        a = float(self._audio_hp_a)
        x1 = float(self._audio_hp_x1)
        y1 = float(self._audio_hp_y1)
        for i in range(x.size):
            xi = float(x[i])
            yi = a * (y1 + xi - x1)
            y[i] = yi
            x1 = xi
            y1 = yi
        self._audio_hp_x1 = x1
        self._audio_hp_y1 = y1
        return y

    # ---------- lifecycle ----------
    def start(self, output_device: Optional[int] = None) -> None:
        if self._running: return
        if output_device is not None:
            self._device_index = output_device
        dev_used = self._device_index
        if dev_used is None:
            try: dev_used = sd.default.device[1]
            except Exception: dev_used = None

        print("[FM] opening audio:", dev_used, self.device_name(dev_used) if dev_used is not None else "(default)")
        _log_fm(f"START: audio_rate={self._audio_rate} Hz, in_rate(now)={self._in_rate} Hz, device={dev_used}")

        self._stream = sd.OutputStream(
            samplerate=self._audio_rate,
            device=dev_used,
            channels=1,
            dtype="float32",
            blocksize=0,
            latency="low",
            callback=self._sd_callback
        )
        self._stream.start()

        # reset
        self._audio_lpf.z = 0.0
        self._deemph.z = 0.0
        self._dc = 0.0
        self._prev_bb = None
        self._audio_hp_x1 = 0.0
        self._audio_hp_y1 = 0.0
        self._last_out = 0.0
        with self._rb_lock:
            self._rb[:] = 0.0
            self._rb_w = self._rb_r = 0

        # NEW: (re)crée le resampler de sortie
        self._out_rs = RationalResampler(self._in_rate, self._audio_rate)

        self._running = True
        _log_fm("Audio callback started.")

    @staticmethod
    def list_output_devices() -> List[Tuple[int, str]]:
        try:
            devices = sd.query_devices()
            apis = sd.query_hostapis()
        except Exception:
            return []
        out = []
        for idx, dev in enumerate(devices):
            try:
                if int(dev.get("max_output_channels", 0)) > 0:
                    api_name = apis[dev["hostapi"]]["name"] if isinstance(dev.get("hostapi"), int) else "?"
                    name = f'{dev.get("name", "?")} ({api_name})'
                    out.append((idx, name))
            except Exception:
                pass
        return out

    @staticmethod
    def device_name(index: int) -> str:
        try:
            dev = sd.query_devices(index)
            api = sd.query_hostapis()[dev["hostapi"]]["name"]
            return f'{dev["name"]} ({api})'
        except Exception:
            return f"Device #{index}"

    def _sd_callback(self, outdata, frames, time_info, status):
        if status:
            _log_fm(f"callback status: {status}")
        now = time.monotonic()
        if self._prefill_needed or now < self._mute_until:
            outdata.fill(0.0); return

        y = self._rb_read(frames)
        if y.size < frames:
            fill_n = frames - y.size
            if y.size == 0:
                out = np.full(frames, self._last_out, dtype=np.float32)
            else:
                out = np.concatenate([y, np.full(fill_n, self._last_out, dtype=np.float32)])
        else:
            out = y

        if self._fade_in_remaining > 0:
            m = min(self._fade_in_remaining, frames)
            ramp = np.linspace(0.0, 1.0, m, dtype=np.float32)
            out[:m] *= ramp
            self._fade_in_remaining -= m

        outdata[:, 0] = out
        self._last_out = float(out[-1]) if out.size else self._last_out

    def stop(self) -> None:
        _log_fm("STOP requested.")
        self._running = False
        try:
            if self._stream is not None:
                self._stream.stop(); self._stream.close()
        except Exception:
            pass
        self._stream = None
        self._out_rs = None
        self._prev_bb = None
        _log_fm("STOP done (stream closed).")

    # ---------- processing ----------
    def process_block(self, bb: np.ndarray, fs_in: float) -> None:
        """
        bb: IQ bande de base déjà à fs_in == desired_input_rate(..)
        On sort de l'audio à self._audio_rate (48 kHz par défaut).
        """
        if not self._running or bb is None or bb.size < 2:
            return

        # 1) discriminateur de phase avec continuité inter-blocs
        x = bb.astype(np.complex64, copy=False)
        if self._prev_bb is not None:
            x = np.concatenate((np.asarray([self._prev_bb], dtype=np.complex64), x))
        # Limiteur IF (inspiré des chaînes FM matures): réduit la sensibilité AM->phase.
        if self._if_limiter:
            x = x / (np.abs(x) + 1e-9)
        dphi = _fm_phase_discriminator(x)
        self._prev_bb = np.complex64(x[-1])

        # 2) retrait DC lent (anti-click)
        self._dc += self._dc_alpha * (float(np.mean(dphi)) - self._dc)
        dphi = dphi - self._dc

        # 3) gain + limiteur optionnel
        audio = (self._gain * dphi).astype(np.float32, copy=False)
        if self._limiter:
            audio = np.tanh(audio).astype(np.float32, copy=False)

        # 4) rééchantillonnage vers la fréquence audio via le module resampler
        if abs(fs_in - self._audio_rate) > 1e-3:
            if self._out_rs is None:
                self._out_rs = RationalResampler(fs_in, self._audio_rate)
                self._in_rate = float(fs_in)
            elif abs(fs_in - self._in_rate) / max(1.0, self._in_rate) > 0.005:
                # Ne pas appeler set_ratio() à chaque bloc: cela reset l'état du resampler.
                self._in_rate = float(fs_in)
                self._out_rs.set_ratio(fs_in, self._audio_rate)
            y = self._out_rs.process(audio)
        else:
            y = audio

        # 5) de-emphasis + LPF (dessinés à self._audio_rate)
        if self._deemph_enable and self._deemph.a > 0.0:
            y = _apply_deemphasis(y, self._deemph)
        y = _apply_one_pole_lpf(y, self._audio_lpf)
        y = self._apply_audio_hp(y)

        # 6) écrire dans le ring buffer (audio callback consommera à 48 kHz)
        self._rb_write(y)

        # throttle des logs "enqueue"
        now = time.monotonic()
        if now - self._last_log_t > 0.25:
            _log_fm(f"enqueue audio: {y.size} frames @ in_fs={fs_in:.2f} -> out={self._audio_rate:.1f}")
            self._last_log_t = now

        # 7) gestion du prefill/unmute (après l’écriture)
        if self._prefill_needed:
            with self._rb_lock:
                avail = self._rb_available()
            if avail >= self._prefill_target:
                self._prefill_needed = False
                self._fade_in_remaining = int(0.02 * self._audio_rate)  # 20 ms
                self._mute_until = 0.0
                _log_fm(f"prefill reached ({avail} >= {self._prefill_target}) — unmute + fade-in")

    # ---------- reconfig ----------
    def begin_reconfig(self, mute_sec: float = 0.25):
        """
        À appeler juste avant un gros changement (FS SDR, BW…).
        On passe en mode “prefill”: mute tant que le ring n’a pas ≥ 200 ms audio.
        """
        self._prefill_needed = True
        self._mute_until = time.monotonic() + float(mute_sec)  # court mute initial
        self._fade_in_remaining = 0
        self._dc = 0.0
        self._prev_bb = None
        self._deemph.z = 0.0
        self._audio_lpf.z = 0.0
        self._audio_hp_x1 = 0.0
        self._audio_hp_y1 = 0.0
        # NEW: on remet à zéro le resampler si présent
        if self._out_rs is not None:
            self._out_rs.reset()
        # on vide proprement (on lit = on met r=w) pour repartir sans vieux samples
        with self._rb_lock:
            self._rb_r = self._rb_w
        _log_fm(f"BEGIN_RECONFIG: mute ~{mute_sec*1000:.0f} ms, prefill target {self._prefill_target} samples")
