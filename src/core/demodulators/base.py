"""Base helpers shared by demodulator implementations."""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass

import numpy as np
import sounddevice as sd

from src.core.dsp.resampler import RationalResampler


@dataclass
class AudioBlock:
    """A demodulated mono audio block."""

    samples: np.ndarray
    sample_rate: float


class BlockDemodulator:
    """Small protocol-like base class for block demodulators."""

    name = "base"

    def demodulate_block(self, iq_data: np.ndarray, sample_rate_hz: float) -> AudioBlock:
        raise NotImplementedError


class AudioOutputDemodulator(BlockDemodulator):
    """Common mono audio sink for block demodulators."""

    def __init__(self, audio_rate: float = 48_000.0, audio_device: int | None = None, gain: float = 0.8) -> None:
        self._audio_rate = float(audio_rate)
        self._in_rate = float(audio_rate)
        self._device_index = audio_device
        self._stream: sd.OutputStream | None = None
        self._running = False
        self._gain = float(gain)

        self._rb_size = int(self._audio_rate * 0.6)
        self._rb = np.zeros(self._rb_size, dtype=np.float32)
        self._rb_w = 0
        self._rb_r = 0
        self._rb_lock = threading.Lock()
        self._last_out = 0.0
        self._out_rs: RationalResampler | None = None
        self._mute_until = 0.0
        self._prefill_needed = False
        self._prefill_target = int(self._audio_rate * 0.15)
        self._recovery_threshold_pct = 10.0
        self._last_audio_rms = 0.0
        self._last_audio_peak = 0.0
        self._audio_clip_events = 0
        self._audio_clip_samples = 0
        self._audio_underrun_events = 0
        self._audio_underrun_frames = 0
        self._audio_overflow_events = 0
        self._audio_overflow_samples = 0
        self._audio_buffer_low_water_pct = 100.0

    def set_input_rate(self, fs_in: float) -> None:
        fs_in = float(fs_in)
        changed = abs(fs_in - self._in_rate) / max(1.0, self._in_rate) > 0.005
        self._in_rate = fs_in
        if changed and self._out_rs is not None:
            self._out_rs.set_ratio(self._in_rate, self._audio_rate)
            self.begin_reconfig()

    def begin_reconfig(self, mute_sec: float = 0.15) -> None:
        self._mute_until = time.monotonic() + float(mute_sec)
        if self._out_rs is not None:
            self._out_rs.reset()
        with self._rb_lock:
            self._rb_r = self._rb_w
            self._audio_buffer_low_water_pct = 100.0
        self._prefill_needed = True

    def start(self, output_device: int | None = None) -> None:
        if self._running:
            return
        if output_device is not None:
            self._device_index = output_device
        device = self._device_index
        if device is None:
            try:
                device = sd.default.device[1]
            except Exception:
                device = None
        self._stream = sd.OutputStream(
            samplerate=self._audio_rate,
            device=device,
            channels=1,
            dtype="float32",
            blocksize=0,
            latency="low",
            callback=self._sd_callback,
        )
        self._stream.start()
        self._out_rs = RationalResampler(self._in_rate, self._audio_rate)
        self._last_out = 0.0
        with self._rb_lock:
            self._rb[:] = 0.0
            self._rb_w = 0
            self._rb_r = 0
            self._audio_buffer_low_water_pct = 100.0
        self.reset_runtime_stats(reset_buffer_metrics=False)
        self._prefill_needed = False
        self._running = True

    def stop(self) -> None:
        self._running = False
        try:
            if self._stream is not None:
                self._stream.stop()
                self._stream.close()
        except Exception:
            pass
        self._stream = None
        self._out_rs = None
        self.reset_runtime_stats()

    def process_block(self, iq_data: np.ndarray, sample_rate_hz: float) -> None:
        if not self._running or iq_data is None or iq_data.size == 0:
            return
        if abs(float(sample_rate_hz) - self._in_rate) / max(1.0, self._in_rate) > 0.005:
            self.set_input_rate(float(sample_rate_hz))

        block = self.demodulate_block(iq_data, float(sample_rate_hz))
        audio = np.asarray(block.samples, dtype=np.float32)
        if audio.size == 0:
            return
        scaled = self._gain * audio
        clip_mask = np.abs(scaled) >= 0.98
        clip_count = int(np.count_nonzero(clip_mask))
        if clip_count:
            self._audio_clip_events += 1
            self._audio_clip_samples += clip_count
        audio = np.clip(scaled, -1.0, 1.0).astype(np.float32, copy=False)

        if abs(float(block.sample_rate) - self._audio_rate) > 1e-3:
            if self._out_rs is None:
                self._out_rs = RationalResampler(float(block.sample_rate), self._audio_rate)
            else:
                self._out_rs.set_ratio(float(block.sample_rate), self._audio_rate)
            audio = self._out_rs.process(audio)

        if audio.size:
            self._last_audio_rms = float(np.sqrt(np.mean(audio * audio)))
            self._last_audio_peak = float(np.max(np.abs(audio)))
        else:
            self._last_audio_rms = 0.0
            self._last_audio_peak = 0.0
        self._rb_write(audio)
        if self._prefill_needed and self._rb_available() >= self._prefill_target:
            self._prefill_needed = False
            self._mute_until = 0.0

    def get_runtime_stats(self) -> dict:
        return {
            "audio_rate_hz": float(self._audio_rate),
            "audio_running": bool(self._running),
            "audio_buffer_fill_pct": 100.0 * self._rb_available() / max(1, self._rb_size),
            "audio_low_water_pct": float(self._audio_buffer_low_water_pct),
            "audio_rms": float(self._last_audio_rms),
            "audio_peak": float(self._last_audio_peak),
            "audio_underruns": int(self._audio_underrun_events),
            "audio_underrun_frames": int(self._audio_underrun_frames),
            "audio_overflows": int(self._audio_overflow_events),
            "audio_overflow_samples": int(self._audio_overflow_samples),
            "audio_clip_events": int(self._audio_clip_events),
            "audio_clip_samples": int(self._audio_clip_samples),
        }

    def reset_runtime_stats(self, reset_buffer_metrics: bool = True) -> None:
        self._last_audio_rms = 0.0
        self._last_audio_peak = 0.0
        self._audio_clip_events = 0
        self._audio_clip_samples = 0
        self._audio_underrun_events = 0
        self._audio_underrun_frames = 0
        self._audio_overflow_events = 0
        self._audio_overflow_samples = 0
        if reset_buffer_metrics:
            self._audio_buffer_low_water_pct = 100.0

    def _sd_callback(self, outdata, frames, time_info, status) -> None:
        now = time.monotonic()
        if (not self._prefill_needed) and self._rb_size > 0:
            fill_pct = 100.0 * self._rb_available() / max(1, self._rb_size)
            if fill_pct < self._recovery_threshold_pct:
                self._prefill_needed = True
                self._mute_until = max(self._mute_until, now + 0.05)
        if self._prefill_needed or now < self._mute_until:
            outdata.fill(0.0)
            return
        out = self._rb_read(frames)
        if out.size < frames:
            self._audio_underrun_events += 1
            self._audio_underrun_frames += int(frames - out.size)
            self._prefill_needed = True
            self._mute_until = max(self._mute_until, now + 0.05)
            fill_n = frames - out.size
            if out.size == 0:
                out = np.full(frames, self._last_out, dtype=np.float32)
            else:
                out = np.concatenate((out, np.full(fill_n, self._last_out, dtype=np.float32)))
        outdata[:, 0] = out
        self._last_out = float(out[-1]) if out.size else self._last_out

    def _rb_space(self) -> int:
        return (self._rb_r - self._rb_w - 1) % self._rb_size

    def _rb_available(self) -> int:
        return (self._rb_w - self._rb_r) % self._rb_size

    def _rb_write(self, samples: np.ndarray) -> None:
        samples = np.asarray(samples, dtype=np.float32)
        if samples.size == 0:
            return
        with self._rb_lock:
            n = min(samples.size, self._rb_space())
            dropped = int(samples.size - n)
            if dropped > 0:
                self._audio_overflow_events += 1
                self._audio_overflow_samples += dropped
            if n <= 0:
                return
            n1 = min(n, self._rb_size - self._rb_w)
            self._rb[self._rb_w:self._rb_w + n1] = samples[:n1]
            self._rb_w = (self._rb_w + n1) % self._rb_size
            n2 = n - n1
            if n2 > 0:
                self._rb[0:n2] = samples[n1:n1 + n2]
                self._rb_w = (self._rb_w + n2) % self._rb_size
            fill_pct = 100.0 * self._rb_available() / max(1, self._rb_size)
            self._audio_buffer_low_water_pct = min(self._audio_buffer_low_water_pct, fill_pct)

    def _rb_read(self, n_frames: int) -> np.ndarray:
        out = np.zeros(n_frames, dtype=np.float32)
        with self._rb_lock:
            n = min(n_frames, self._rb_available())
            if n <= 0:
                self._audio_buffer_low_water_pct = min(self._audio_buffer_low_water_pct, 0.0)
                return out[:0]
            n1 = min(n, self._rb_size - self._rb_r)
            out[:n1] = self._rb[self._rb_r:self._rb_r + n1]
            self._rb_r = (self._rb_r + n1) % self._rb_size
            n2 = n - n1
            if n2 > 0:
                out[n1:n1 + n2] = self._rb[0:n2]
                self._rb_r = (self._rb_r + n2) % self._rb_size
            fill_pct = 100.0 * self._rb_available() / max(1, self._rb_size)
            self._audio_buffer_low_water_pct = min(self._audio_buffer_low_water_pct, fill_pct)
        return out[:n]

    @staticmethod
    def list_output_devices():
        try:
            devices = sd.query_devices()
            apis = sd.query_hostapis()
        except Exception:
            return []
        outputs = []
        for idx, dev in enumerate(devices):
            try:
                if int(dev.get("max_output_channels", 0)) > 0:
                    api_name = apis[dev["hostapi"]]["name"] if isinstance(dev.get("hostapi"), int) else "?"
                    outputs.append((idx, f'{dev.get("name", "?")} ({api_name})'))
            except Exception:
                pass
        return outputs

    @staticmethod
    def device_name(index: int) -> str:
        try:
            dev = sd.query_devices(index)
            api = sd.query_hostapis()[dev["hostapi"]]["name"]
            return f'{dev["name"]} ({api})'
        except Exception:
            return f"Device #{index}"
