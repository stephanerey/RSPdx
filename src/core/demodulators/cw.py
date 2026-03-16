"""CW demodulation helpers."""

from __future__ import annotations

import numpy as np

from .base import AudioBlock, AudioOutputDemodulator, BlockDemodulator
from .ssb import demodulate_ssb


def demodulate_cw(iq_data: np.ndarray, tone_frequency_hz: float, sample_rate_hz: float) -> np.ndarray:
    iq = np.asarray(iq_data, dtype=np.complex64)
    if iq.size == 0:
        return np.zeros(0, dtype=np.float32)
    n = np.arange(iq.size, dtype=np.float32)
    tone = np.exp(-1j * 2.0 * np.pi * float(tone_frequency_hz) * n / float(sample_rate_hz))
    shifted = iq * tone.astype(np.complex64, copy=False)
    return demodulate_ssb(shifted, sideband="usb")


class CWDemodulator(BlockDemodulator):
    name = "cw"

    def __init__(self, tone_frequency_hz: float = 700.0) -> None:
        self.tone_frequency_hz = float(tone_frequency_hz)

    def demodulate_block(self, iq_data: np.ndarray, sample_rate_hz: float) -> AudioBlock:
        samples = demodulate_cw(iq_data, self.tone_frequency_hz, sample_rate_hz)
        return AudioBlock(samples=samples, sample_rate=float(sample_rate_hz))


class CWAudioDemodulator(AudioOutputDemodulator):
    name = "cw"

    def __init__(
        self,
        tone_frequency_hz: float = 700.0,
        audio_rate: float = 48_000.0,
        audio_device: int | None = None,
    ) -> None:
        super().__init__(audio_rate=audio_rate, audio_device=audio_device, gain=0.8)
        self.tone_frequency_hz = float(tone_frequency_hz)

    def demodulate_block(self, iq_data: np.ndarray, sample_rate_hz: float) -> AudioBlock:
        samples = demodulate_cw(iq_data, self.tone_frequency_hz, sample_rate_hz)
        return AudioBlock(samples=samples, sample_rate=float(sample_rate_hz))
