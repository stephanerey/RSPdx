"""Decimation helpers."""

from __future__ import annotations

import numpy as np


def vector_decimate(iq_data: np.ndarray, factor: int) -> np.ndarray:
    if int(factor) <= 1:
        return np.asarray(iq_data, dtype=np.complex64)
    return np.asarray(iq_data, dtype=np.complex64)[:: int(factor)]


def streaming_decimate(iq_data: np.ndarray, factor: int, phase: int = 0) -> tuple[np.ndarray, int]:
    """Decimate a block while keeping a streaming phase accumulator."""
    factor = int(max(1, factor))
    data = np.asarray(iq_data, dtype=np.complex64)
    if factor <= 1 or data.size == 0:
        return data, 0
    n_in = int(data.size)
    start = (-int(phase)) % factor
    decimated = data[start::factor]
    next_phase = (int(phase) + n_in) % factor
    return decimated.astype(np.complex64, copy=False), next_phase

