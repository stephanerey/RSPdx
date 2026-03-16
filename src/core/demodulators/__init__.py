"""Demodulation modules for the SDR core."""

from .am import AMAudioDemodulator, AMDemodulator, demodulate_am
from .cw import CWAudioDemodulator, CWDemodulator, demodulate_cw
from .fm import FMAudioMode, FMDemodulator
from .registry import build_block_demodulator_registry, build_demodulator_registry
from .ssb import SSBAudioDemodulator, SSBDemodulator, demodulate_ssb

__all__ = [
    "AMAudioDemodulator",
    "AMDemodulator",
    "CWAudioDemodulator",
    "CWDemodulator",
    "FMAudioMode",
    "FMDemodulator",
    "SSBAudioDemodulator",
    "SSBDemodulator",
    "build_block_demodulator_registry",
    "build_demodulator_registry",
    "demodulate_am",
    "demodulate_cw",
    "demodulate_ssb",
]
