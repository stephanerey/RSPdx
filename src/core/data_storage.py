from PyQt5 import QtCore
import numpy as np
from src.utils.misc import smooth

class HistoryBuffer:
    def __init__(self, data_size, max_history_size, dtype=float):
        self.data_size = data_size
        self.max_history_size = max_history_size
        self.history_size = 0
        self.counter = 0
        self.buffer = np.empty(shape=(max_history_size, data_size), dtype=dtype)
    def append(self, data):
        self.counter += 1
        if self.history_size < self.max_history_size:
            self.history_size += 1
        self.buffer = np.roll(self.buffer, -1, axis=0)
        self.buffer[-1] = data
    def get_buffer(self):
        return self.buffer[-self.history_size:] if self.history_size < self.max_history_size else self.buffer
    def __getitem__(self, key): return self.buffer[key]

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
        self.smooth = False
        self.smooth_length = 11
        self.smooth_window = "hanning"
        self.subtract_baseline = False
        self.prev_baseline = None
        self.baseline = None
        self.baseline_x = None
        self.threadpool = QtCore.QThreadPool()
        self.threadpool.setMaxThreadCount(1)
        self.reset()

    def reset(self):
        self.wait()
        self.x = None
        self.history = None
        self.reset_data()

    def reset_data(self):
        self.wait()
        self.y = None
        self.average_counter = 0
        self.average = None
        self.peak_hold_max = None
        self.peak_hold_min = None

    def start_task(self, fn, *args, **kwargs):
        task = Task(fn, *args, **kwargs)
        self.threadpool.start(task)

    def wait(self):
        self.threadpool.waitForDone()

    def update(self, data):
        if self.y is not None and len(data["y"]) != len(self.y):
            print(f"{len(data['y']):d} bins coming from backend, expected {len(self.y):d}")
            return
        self.average_counter += 1
        self.x = np.array(data["x"])
        data["y"] = np.asarray(data["y"])
        if self.subtract_baseline and self.baseline is not None and len(data["y"]) == len(self.baseline):
            data["y"] -= self.baseline
        self.start_task(self.update_history, data.copy())
        self.start_task(self.update_data, data)

    def update_data(self, data):
        if self.smooth:
            data["y"] = self.smooth_data(data["y"])
        self.y = data["y"]
        self.data_updated.emit(self)
        self.start_task(self.update_average, data)
        self.start_task(self.update_peak_hold_max, data)
        self.start_task(self.update_peak_hold_min, data)

    def update_history(self, data):
        if self.history is None:
            self.history = HistoryBuffer(len(data["y"]), self.max_history_size)
        self.history.append(data["y"])
        self.history_updated.emit(self)

    def update_average(self, data):
        if self.average is None:
            self.average = data["y"].copy()
        else:
            self.average = np.average((self.average, data["y"]), axis=0, weights=(self.average_counter - 1, 1))
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
            self.start_task(self.recalculate_data)

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
