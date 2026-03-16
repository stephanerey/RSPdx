"""AM demodulator helpers."""

from __future__ import annotations

import numpy as np

from .base import AudioBlock, AudioOutputDemodulator, BlockDemodulator


def demodulate_am(iq_data: np.ndarray) -> np.ndarray:
    iq = np.asarray(iq_data, dtype=np.complex64)
    if iq.size == 0:
        return np.zeros(0, dtype=np.float32)
    envelope = np.abs(iq).astype(np.float32, copy=False)
    envelope -= float(np.mean(envelope))
    peak = float(np.max(np.abs(envelope))) if envelope.size else 0.0
    if peak > 1e-12:
        envelope /= peak
    return envelope.astype(np.float32, copy=False)


class AMDemodulator(BlockDemodulator):
    name = "am"

    def demodulate_block(self, iq_data: np.ndarray, sample_rate_hz: float) -> AudioBlock:
        return AudioBlock(samples=demodulate_am(iq_data), sample_rate=float(sample_rate_hz))


class AMAudioDemodulator(AudioOutputDemodulator):
    name = "am"

    def __init__(self, audio_rate: float = 48_000.0, audio_device: int | None = None) -> None:
        super().__init__(audio_rate=audio_rate, audio_device=audio_device, gain=0.9)

    def demodulate_block(self, iq_data: np.ndarray, sample_rate_hz: float) -> AudioBlock:
        return AudioBlock(samples=demodulate_am(iq_data), sample_rate=float(sample_rate_hz))
