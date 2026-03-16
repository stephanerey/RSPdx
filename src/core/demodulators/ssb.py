"""SSB demodulation helpers for USB and LSB."""

from __future__ import annotations

import numpy as np

from .base import AudioBlock, AudioOutputDemodulator, BlockDemodulator


def demodulate_ssb(iq_data: np.ndarray, sideband: str = "usb") -> np.ndarray:
    iq = np.asarray(iq_data, dtype=np.complex64)
    if iq.size == 0:
        return np.zeros(0, dtype=np.float32)

    spectrum = np.fft.fftshift(np.fft.fft(iq))
    midpoint = spectrum.size // 2
    if str(sideband).lower() == "usb":
        spectrum[:midpoint] = 0.0
    else:
        spectrum[midpoint:] = 0.0

    filtered = np.fft.ifft(np.fft.ifftshift(spectrum))
    audio = np.real(filtered).astype(np.float32, copy=False)
    audio -= float(np.mean(audio))
    peak = float(np.max(np.abs(audio))) if audio.size else 0.0
    if peak > 1e-12:
        audio /= peak
    return audio


class SSBDemodulator(BlockDemodulator):
    name = "ssb"

    def __init__(self, sideband: str = "usb") -> None:
        self.sideband = str(sideband).lower()

    def demodulate_block(self, iq_data: np.ndarray, sample_rate_hz: float) -> AudioBlock:
        samples = demodulate_ssb(iq_data, sideband=self.sideband)
        return AudioBlock(samples=samples, sample_rate=float(sample_rate_hz))


class SSBAudioDemodulator(AudioOutputDemodulator):
    name = "ssb"

    def __init__(self, sideband: str = "usb", audio_rate: float = 48_000.0, audio_device: int | None = None) -> None:
        super().__init__(audio_rate=audio_rate, audio_device=audio_device, gain=0.8)
        self.sideband = str(sideband).lower()

    def demodulate_block(self, iq_data: np.ndarray, sample_rate_hz: float) -> AudioBlock:
        samples = demodulate_ssb(iq_data, sideband=self.sideband)
        return AudioBlock(samples=samples, sample_rate=float(sample_rate_hz))
