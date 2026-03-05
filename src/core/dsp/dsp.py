import numpy as np
from scipy.signal import firwin, lfilter

def mix_to_baseband(iq: np.ndarray, f_offset_hz: float, fs: float) -> np.ndarray:
    """Translation de fréquence: mélange vers 0 Hz."""
    if f_offset_hz == 0.0:
        return iq
    n = np.arange(len(iq), dtype=np.float32)
    osc = np.exp(-1j * 2.0 * np.pi * f_offset_hz * n / fs)
    return iq * osc

def design_lpf_fir(cutoff_hz: float, fs: float, num_taps: int = 511, window: str = "hamming"):
    """FIR LPF (linéaire phase). cutoff_hz en Hz (bords à -6 dB env.)."""
    nyq = 0.5 * fs
    w = min(max(cutoff_hz / nyq, 1e-6), 0.999)
    taps = firwin(num_taps, w, window=window)
    return taps

def apply_fir(iq: np.ndarray, taps: np.ndarray) -> np.ndarray:
    """Filtrage FIR causal simple."""
    return lfilter(taps, [1.0], iq)

def safe_decimate(iq: np.ndarray, factor: int) -> np.ndarray:
    """Décimation naïve (post-FIR)."""
    if factor <= 1:
        return iq
    return iq[::factor]

def costas_loop(iq: np.ndarray, fs: float, loop_bw: float = 0.01, damping: float = 0.707, mode: str = "qpsk"):
    """
    Boucle de Costas simple (decision-directed). Retourne IQ corrigé.
    - mode: "qpsk" (défaut) ou "bpsk"
    """
    if len(iq) == 0:
        return iq

    # Coeffs de PLL discrets (normalisés), efficaces en streaming bloc.
    # loop_bw est une bande de boucle normalisée (≈ 0.001 .. 0.05).
    bw = max(1e-5, float(loop_bw))
    zeta = max(0.1, float(damping))
    den = 1.0 + 2.0 * zeta * bw + bw * bw
    alpha = (4.0 * zeta * bw) / den
    beta = (4.0 * bw * bw) / den

    phase = 0.0
    freq = 0.0

    out = np.empty_like(iq, dtype=np.complex64)

    for i, s in enumerate(iq):
        nco = np.exp(-1j * phase)
        y = s * nco
        if mode == "bpsk":
            err = np.sign(np.real(y)) * np.imag(y)
        else:  # QPSK
            err = np.sign(np.real(y)) * np.imag(y) - np.sign(np.imag(y)) * np.real(y)

        freq += beta * err
        phase += freq + alpha * err

        if phase > np.pi:
            phase -= 2 * np.pi
        elif phase < -np.pi:
            phase += 2 * np.pi

        out[i] = y

    return out
