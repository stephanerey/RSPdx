from __future__ import annotations
import numpy as np
from fractions import Fraction
from dataclasses import dataclass
from typing import Optional

# ---------- Debug logging ----------
DEBUG_RESAMPLER = False  # passe à True pour diagnostiquer

def _log_rs(*args):
    if DEBUG_RESAMPLER:
        print("[RS]", *args)

@dataclass
class ResampleRatio:
    L: int
    M: int
    r_float: float  # fs_out / fs_in (réel)

class RationalResampler:
    """
    Resampler générique L/M (stateful, flux streaming).
    - Fast-path entier (décimation k) avec FIR Hamming court si fs_in ≈ k*fs_out.
    - Sinon, fallback linéaire étatful (stable, léger).
    -> Conçu pour être instancié une fois par branche (démod) et tourner en parallèle.
    """
    def __init__(self, fs_in: float, fs_out: float, max_den: int = 512):
        self._max_den = int(max_den)
        self._fs_in   = float(fs_in)
        self._fs_out  = float(fs_out)

        # état pour le chemin linéaire
        self._lin_pos  = 0.0
        self._lin_prev = 0.0

        # FIR pour fast-path entier
        self._fir     : Optional[np.ndarray] = None
        self._fir_fs  : Optional[float] = None

        # calcul ratio initial
        self._ratio = self._pick_ratio(self._fs_in, self._fs_out)
        _log_rs(f"init: fs_in={self._fs_in:.3f} -> fs_out={self._fs_out:.3f} "
                f"(r≈{self._ratio.L}/{self._ratio.M}={self._ratio.r_float:.6f})")

    # -------- API ----------
    def set_ratio(self, fs_in: float, fs_out: float):
        fs_in  = float(fs_in)
        fs_out = float(fs_out)
        changed = (abs(fs_in  - self._fs_in )/max(1.0, self._fs_in ) > 1e-9) or \
                  (abs(fs_out - self._fs_out)/max(1.0, self._fs_out) > 1e-9)
        if not changed:
            return
        self._fs_in, self._fs_out = fs_in, fs_out
        self._ratio = self._pick_ratio(fs_in, fs_out, self._max_den)
        # reset états
        self._lin_pos = 0.0
        self._lin_prev = 0.0
        # invalide FIR fast-path (sera redésigné si utilisé)
        self._fir = None
        self._fir_fs = None
        _log_rs(f"set_ratio: fs_in={fs_in:.3f} -> fs_out={fs_out:.3f} "
                f"(r≈{self._ratio.L}/{self._ratio.M}={self._ratio.r_float:.6f})")

    def reset(self):
        self._lin_pos  = 0.0
        self._lin_prev = 0.0

    def process(self, x: np.ndarray) -> np.ndarray:
        """
        Traite un bloc (stateful). Renvoie x rééchantillonné de fs_in vers fs_out.
        Sélectionne automatiquement:
          - fast-path entier (FIR + décim k)
          - sinon linéaire étatful
        """
        if x is None or x.size == 0:
            return np.zeros(0, dtype=np.float32)
        x = x.astype(np.float32, copy=False)

        # 1) fast-path entier si fs_in ≈ k * fs_out
        ratio = self._fs_in / self._fs_out if self._fs_out > 0 else 1.0
        k = int(round(ratio))
        if k >= 2 and abs(ratio - k) < 1e-2:  # ~1% de tolérance
            return self._process_integer_decim(x, k)

        # 2) fallback linéaire étatful
        return self._process_linear(x, self._fs_in, self._fs_out)

    # --------- internes ----------
    @staticmethod
    def _pick_ratio(fs_in: float, fs_out: float, max_den: int = 512) -> ResampleRatio:
        if fs_in <= 0 or fs_out <= 0:
            return ResampleRatio(1, 1, 1.0)
        r = fs_out / fs_in
        frac = Fraction.from_float(r).limit_denominator(max_den)
        return ResampleRatio(frac.numerator, frac.denominator, r)

    @staticmethod
    def _design_fir_hamming(fs: float, cutoff_hz: float, n: int = 63) -> np.ndarray:
        """
        Petit FIR passe-bas (Hamming) pour la décimation entière.
        cutoff_hz = ~0.45 * fs_out/2 est une valeur raisonnable.
        """
        t = np.arange(n, dtype=np.float64) - (n - 1) / 2
        h = np.sinc(2.0 * cutoff_hz / fs * t)
        w = 0.54 - 0.46 * np.cos(2.0 * np.pi * np.arange(n, dtype=np.float64) / (n - 1))
        h = (h * w)
        h /= np.sum(h)
        return h.astype(np.float32)

    def _ensure_fir_for_integer(self):
        if self._fir is not None and self._fir_fs == self._fs_in:
            return
        # marge confortable vs fs_out
        cutoff = 0.45 * (self._fs_out * 0.5)
        self._fir = self._design_fir_hamming(self._fs_in, cutoff, n=63)
        self._fir_fs = self._fs_in
        _log_rs(f"design FIR integer-path: fs_in={self._fs_in:.1f}, cutoff={cutoff:.1f} Hz, taps={self._fir.size}")

    def _process_integer_decim(self, x: np.ndarray, k: int) -> np.ndarray:
        self._ensure_fir_for_integer()
        y = np.convolve(x, self._fir, mode="same")
        out = y[::k].astype(np.float32, copy=False)
        _log_rs(f"integer decim: k={k}, in_len={x.size}, out_len={out.size}")
        return out

    def _process_linear(self, x: np.ndarray, fs_in: float, fs_out: float) -> np.ndarray:
        """
        Rééchantillonnage linéaire étatful bloc-par-bloc (cheap & stable).
        """
        if fs_in <= 0 or fs_out <= 0:
            return np.zeros(0, dtype=np.float32)

        step = fs_in / fs_out  # nb d'échantillons d'entrée par échantillon de sortie
        pos  = float(self._lin_pos)

        # on construit un tampon [prev] + x[0..] pour interpoler proprement au bord de bloc
        buf = np.empty(x.size + 1, dtype=np.float32)
        buf[0] = float(self._lin_prev)
        buf[1:] = x

        out = []
        n_in = buf.size - 1
        while pos + 1.0 < n_in + 1e-12:
            i0 = int(pos)
            frac = pos - i0
            y = (1.0 - frac) * buf[i0] + frac * buf[i0 + 1]
            out.append(y)
            pos += step

        # mettre à jour l’état
        self._lin_pos  = pos - n_in
        self._lin_prev = float(buf[-1])

        out = np.asarray(out, dtype=np.float32) if out else np.zeros(0, dtype=np.float32)
        _log_rs(f"linear path: fs_in={fs_in:.1f} -> fs_out={fs_out:.1f}, in_len={x.size}, out_len={out.size}")
        return out
