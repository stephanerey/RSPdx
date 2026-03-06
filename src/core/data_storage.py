from PyQt5 import QtCore
import numpy as np
from src.utils.misc import smooth

class HistoryBuffer:
    def __init__(self, data_size, max_history_size, dtype=float):
        self.data_size = data_size
        self.max_history_size = max_history_size
        self.history_size = 0
        self.counter = 0
        self.write_pos = 0
        self.buffer = np.empty(shape=(max_history_size, data_size), dtype=dtype)
    def append(self, data):
        self.counter += 1
        self.buffer[self.write_pos] = data
        self.write_pos = (self.write_pos + 1) % self.max_history_size
        if self.history_size < self.max_history_size:
            self.history_size += 1

    def get_recent(self, count):
        count = int(max(0, min(int(count), self.history_size)))
        if count == 0:
            return self.buffer[:0]
        if self.history_size < self.max_history_size:
            return self.buffer[self.history_size - count:self.history_size]
        end = self.write_pos
        start = (end - count) % self.max_history_size
        if start < end:
            return self.buffer[start:end]
        return np.concatenate((self.buffer[start:], self.buffer[:end]), axis=0)

    def get_buffer(self):
        return self.get_recent(self.history_size)
    def __getitem__(self, key):
        return self.get_buffer()[key]

class TaskSignals(QtCore.QObject):
    result = QtCore.pyqtSignal(object)

class Task(QtCore.QRunnable):
    def __init__(self, task, *args, **kwargs):
        super().__init__()
        self.task = task
        self.args = args
        self.kwargs = kwargs
        self.signals = TaskSignals()
    def run(self):
        result = self.task(*self.args, **self.kwargs)
        self.signals.result.emit(result)

class DataStorage(QtCore.QObject):
    history_updated = QtCore.pyqtSignal(object)
    data_updated = QtCore.pyqtSignal(object)
    history_recalculated = QtCore.pyqtSignal(object)
    data_recalculated = QtCore.pyqtSignal(object)
    average_updated = QtCore.pyqtSignal(object)
    baseline_updated = QtCore.pyqtSignal(object)
    peak_hold_max_updated = QtCore.pyqtSignal(object)
    peak_hold_min_updated = QtCore.pyqtSignal(object)

    def __init__(self, max_history_size=100, parent=None):
        super().__init__(parent)
        self.max_history_size = max_history_size
        self.waterfall_max_bins = 32768
        self.waterfall_time_stride = 2
        self.smooth = False
        self.smooth_length = 11
        self.smooth_window = "hanning"
        self.subtract_baseline = False
        self.compute_average_enabled = False
        self.compute_peak_max_enabled = False
        self.compute_peak_min_enabled = False
        self.prev_baseline = None
        self.baseline = None
        self.baseline_x = None
        self.reset()

    def reset(self):
        self.x = None
        self.x_wf = None
        self.history = None
        self.waterfall_history = None
        self._waterfall_frame_counter = 0
        self.reset_data()

    def reset_data(self):
        self.y = None
        self.average_counter = 0
        self.average = None
        self.peak_hold_max = None
        self.peak_hold_min = None

    def start_task(self, fn, *args, **kwargs):
        # Chemin synchrone pour éviter l'accumulation de tâches UI/worker.
        fn(*args, **kwargs)

    def wait(self):
        return

    def update(self, data):
        if self.y is not None and len(data["y"]) != len(self.y):
            print(f"{len(data['y']):d} bins coming from backend, expected {len(self.y):d} - resetting storage")
            self.x = None
            self.x_wf = None
            self.history = None
            self.waterfall_history = None
            self._waterfall_frame_counter = 0
            self.reset_data()
        x_in = np.asarray(data["x"], dtype=np.float64)
        if self.x is None or self.x.shape != x_in.shape or float(self.x[0]) != float(x_in[0]) or float(self.x[-1]) != float(x_in[-1]):
            self.x = x_in.copy()
            self.x_wf = self._decimate_x_for_waterfall(self.x)
        data["y"] = np.asarray(data["y"], dtype=np.float32)
        if self.subtract_baseline and self.baseline is not None and len(data["y"]) == len(self.baseline):
            data["y"] -= self.baseline
        if self.compute_average_enabled:
            self.average_counter += 1
        self.update_history(data.copy())
        self.update_data(data)

    def update_data(self, data):
        if self.smooth:
            data["y"] = self.smooth_data(data["y"])
        self.y = data["y"]
        self.data_updated.emit(self)
        # Calculs dérivés seulement quand activés par l'UI.
        if self.compute_average_enabled:
            self.update_average(data)
        if self.compute_peak_max_enabled:
            self.update_peak_hold_max(data)
        if self.compute_peak_min_enabled:
            self.update_peak_hold_min(data)

    def update_history(self, data):
        if self.history is None:
            self.history = HistoryBuffer(len(data["y"]), self.max_history_size, dtype=np.float32)
        self.history.append(data["y"])
        self._waterfall_frame_counter += 1
        if self._waterfall_frame_counter % max(1, int(self.waterfall_time_stride)) == 0:
            y_wf = self._decimate_for_waterfall(data["y"])
            if self.waterfall_history is None or self.waterfall_history.data_size != len(y_wf):
                self.waterfall_history = HistoryBuffer(len(y_wf), self.max_history_size, dtype=np.float32)
            self.waterfall_history.append(y_wf)
            self.history_updated.emit(self)

    def _decimate_x_for_waterfall(self, x):
        x = np.asarray(x, dtype=np.float64)
        n = int(x.size)
        if n <= int(self.waterfall_max_bins):
            return x.copy()
        step = int(np.ceil(n / float(self.waterfall_max_bins)))
        return x[::step].copy()

    def _decimate_for_waterfall(self, y):
        y = np.asarray(y, dtype=np.float32)
        n = int(y.size)
        if n <= int(self.waterfall_max_bins):
            return y
        step = int(np.ceil(n / float(self.waterfall_max_bins)))
        m = int(np.ceil(n / float(step)))
        pad = m * step - n
        if pad > 0:
            y_pad = np.pad(y, (0, pad), mode="edge")
        else:
            y_pad = y
        y_r = y_pad.reshape(m, step)
        return np.percentile(y_r, 90.0, axis=1).astype(np.float32, copy=False)

    def set_compute_average_enabled(self, enabled):
        self.compute_average_enabled = bool(enabled)
        if not self.compute_average_enabled:
            self.average = None
            self.average_counter = 0

    def set_compute_peak_max_enabled(self, enabled):
        self.compute_peak_max_enabled = bool(enabled)
        if not self.compute_peak_max_enabled:
            self.peak_hold_max = None

    def set_compute_peak_min_enabled(self, enabled):
        self.compute_peak_min_enabled = bool(enabled)
        if not self.compute_peak_min_enabled:
            self.peak_hold_min = None

    def update_average(self, data):
        if self.average is None:
            self.average = data["y"].copy()
        else:
            n = float(max(1, self.average_counter))
            self.average += (data["y"] - self.average) / n
        self.average_updated.emit(self)

    def update_peak_hold_max(self, data):
        if self.peak_hold_max is None:
            self.peak_hold_max = data["y"].copy()
        else:
            self.peak_hold_max = np.maximum(self.peak_hold_max, data["y"])
            self.peak_hold_max_updated.emit(self)

    def update_peak_hold_min(self, data):
        if self.peak_hold_min is None:
            self.peak_hold_min = data["y"].copy()
        else:
            self.peak_hold_min = np.minimum(self.peak_hold_min, data["y"])
            self.peak_hold_min_updated.emit(self)

    def smooth_data(self, y):
        return smooth(y, window_len=self.smooth_length, window=self.smooth_window)

    def set_smooth(self, toggle, length=11, window="hanning"):
        if toggle != self.smooth or length != self.smooth_length or window != self.smooth_window:
            self.smooth = toggle
            self.smooth_length = length
            self.smooth_window = window
            self.recalculate_data()

    def recalculate_history(self):
        if self.history is None: return
        history = self.history.get_buffer()
        if self.prev_baseline is not None and len(history[-1]) == len(self.prev_baseline):
            history += self.prev_baseline
            self.prev_baseline = None
        if self.subtract_baseline and self.baseline is not None and len(history[-1]) == len(self.baseline):
            history -= self.baseline
        self.history_recalculated.emit(self)

    def recalculate_data(self):
        if self.history is None: return
        history = self.history.get_buffer()
        if self.smooth:
            self.y = self.smooth_data(history[-1])
            self.average_counter = 0
            self.average = self.y.copy()
            self.peak_hold_max = self.y.copy()
            self.peak_hold_min = self.y.copy()
            for y in history[:-1]:
                self.average_counter += 1
                y = self.smooth_data(y)
                self.average = np.average((self.average, y), axis=0, weights=(self.average_counter - 1, 1))
                self.peak_hold_max = np.maximum(self.peak_hold_max, y)
                self.peak_hold_min = np.minimum(self.peak_hold_min, y)
        else:
            self.y = history[-1]
            self.average_counter = self.history.history_size
            self.average = np.average(history, axis=0)
            self.peak_hold_max = history.max(axis=0)
            self.peak_hold_min = history.min(axis=0)
        self.data_recalculated.emit(self)
