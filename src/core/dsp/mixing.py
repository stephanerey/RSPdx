"""Frequency translation helpers."""

from __future__ import annotations

import numpy as np


def mix_to_baseband(iq_data: np.ndarray, frequency_offset_hz: float, sample_rate_hz: float) -> np.ndarray:
    """Translate an IQ vector to baseband."""
    if frequency_offset_hz == 0.0:
        return iq_data
    n = np.arange(len(iq_data), dtype=np.float32)
    oscillator = np.exp(-1j * 2.0 * np.pi * frequency_offset_hz * n / sample_rate_hz)
    return iq_data * oscillator


def mix_to_baseband_block(
    iq_data: np.ndarray,
    frequency_offset_hz: float,
    sample_rate_hz: float,
    initial_phase: float = 0.0,
) -> tuple[np.ndarray, float]:
    """Translate a streaming IQ block while keeping phase continuity."""
    if iq_data is None or iq_data.size == 0 or abs(frequency_offset_hz) < 1e-12 or sample_rate_hz <= 0.0:
        return np.asarray(iq_data, dtype=np.complex64), float(initial_phase)
    step = -2.0 * np.pi * float(frequency_offset_hz) / float(sample_rate_hz)
    n = np.arange(iq_data.size, dtype=np.float32)
    phase = float(initial_phase) + step * n
    oscillator = np.exp(1j * phase).astype(np.complex64, copy=False)
    mixed = np.asarray(iq_data, dtype=np.complex64) * oscillator
    next_phase = float((float(initial_phase) + step * iq_data.size) % (2.0 * np.pi))
    return mixed.astype(np.complex64, copy=False), next_phase

