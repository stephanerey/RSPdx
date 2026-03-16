"""Factory and registry helpers for demodulators."""

from __future__ import annotations

from typing import Callable

from .am import AMAudioDemodulator, AMDemodulator
from .cw import CWAudioDemodulator, CWDemodulator
from .fm import FMDemodulator
from .ssb import SSBAudioDemodulator, SSBDemodulator


DemodulatorFactory = Callable[[], object]


def build_demodulator_registry() -> dict[str, DemodulatorFactory]:
    return {
        "fm": FMDemodulator,
        "am": AMAudioDemodulator,
        "usb": lambda: SSBAudioDemodulator(sideband="usb"),
        "lsb": lambda: SSBAudioDemodulator(sideband="lsb"),
        "cw": CWAudioDemodulator,
    }


def build_block_demodulator_registry() -> dict[str, DemodulatorFactory]:
    return {
        "am": AMDemodulator,
        "usb": lambda: SSBDemodulator(sideband="usb"),
        "lsb": lambda: SSBDemodulator(sideband="lsb"),
        "cw": CWDemodulator,
    }
