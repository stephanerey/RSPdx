"""Filter design and filtering helpers."""

from __future__ import annotations

import numpy as np
from scipy.signal import firwin, lfilter


def design_lpf_fir(cutoff_hz: float, sample_rate_hz: float, num_taps: int = 511, window: str = "hamming") -> np.ndarray:
    """Design a low-pass FIR filter."""
    nyquist = 0.5 * float(sample_rate_hz)
    normalized = min(max(float(cutoff_hz) / max(nyquist, 1.0), 1e-6), 0.999)
    return firwin(int(num_taps), normalized, window=window)


def apply_fir(iq_data: np.ndarray, taps: np.ndarray) -> np.ndarray:
    return lfilter(taps, [1.0], iq_data)


def apply_ema(values: np.ndarray, previous: np.ndarray | None, alpha: float = 0.2) -> np.ndarray:
    """Apply an exponential moving average on a vector."""
    values = np.asarray(values, dtype=np.float32)
    if previous is None or previous.shape != values.shape:
        return values.copy()
    alpha = float(np.clip(alpha, 0.01, 1.0))
    return ((1.0 - alpha) * previous + alpha * values).astype(np.float32, copy=False)

