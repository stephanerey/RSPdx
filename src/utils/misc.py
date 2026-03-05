import numpy as np
from PyQt5 import QtGui

def smooth(x, window_len=11, window='hanning'):
    x = np.array(x)
    if window_len < 3:
        return x
    if x.size < window_len:
        raise ValueError("Input data length must be greater than window size")
    if window not in ['rectangular', 'hanning', 'hamming', 'bartlett', 'blackman']:
        raise ValueError("Window must be 'rectangular', 'hanning', 'hamming', 'bartlett' or 'blackman'")
    w = np.ones(window_len, 'd') if window == 'rectangular' else getattr(np, window)(window_len)
    s = np.r_[2*x[0] - x[window_len:1:-1], x, 2*x[-1] - x[-1:-window_len:-1]]
    y = np.convolve(w / w.sum(), s, mode='same')
    return y[window_len - 1:-window_len + 1]

def str_to_color(color_string):
    return QtGui.QColor(*[int(c.strip()) for c in color_string.split(',')])

def color_to_str(color):
    return ", ".join([str(color.red()), str(color.green()), str(color.blue()), str(color.alpha())])

def human_time(seconds):
    seconds = int(seconds)
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    if h > 0: return f'{h:.0f} h {m:.0f} min {s:.0f} s'
    if m > 0: return f'{m:.0f} min {s:.0f} s'
    return f'{s:.0f} s'
