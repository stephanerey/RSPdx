"""Compatibility facade for legacy DSP imports."""

from __future__ import annotations

import numpy as np

from .decimation import vector_decimate
from .filters import apply_fir, design_lpf_fir
from .mixing import mix_to_baseband


def safe_decimate(iq: np.ndarray, factor: int) -> np.ndarray:
    return vector_decimate(iq, factor)


def costas_loop(
    iq: np.ndarray,
    fs: float,
    loop_bw: float = 0.01,
    damping: float = 0.707,
    mode: str = "qpsk",
) -> np.ndarray:
    """Simple decision-directed Costas loop for complex IQ vectors."""
    if len(iq) == 0:
        return iq

    bw = max(1e-5, float(loop_bw))
    zeta = max(0.1, float(damping))
    den = 1.0 + 2.0 * zeta * bw + bw * bw
    alpha = (4.0 * zeta * bw) / den
    beta = (4.0 * bw * bw) / den

    phase = 0.0
    freq = 0.0
    out = np.empty_like(iq, dtype=np.complex64)

    for idx, sample in enumerate(iq):
        nco = np.exp(-1j * phase)
        value = sample * nco
        if mode == "bpsk":
            error = np.sign(np.real(value)) * np.imag(value)
        else:
            error = np.sign(np.real(value)) * np.imag(value) - np.sign(np.imag(value)) * np.real(value)

        freq += beta * error
        phase += freq + alpha * error
        if phase > np.pi:
            phase -= 2 * np.pi
        elif phase < -np.pi:
            phase += 2 * np.pi

        out[idx] = value

    return out

