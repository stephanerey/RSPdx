import time
import threading
import numpy as np
import SoapySDR
from SoapySDR import SOAPY_SDR_RX, SOAPY_SDR_CF32
from PyQt5 import QtCore
from PyQt5.QtCore import QObject, pyqtSignal
from scipy.signal import lfilter
from src.core.data_storage import DataStorage
from src.config.settings import DEFAULT_SAMPLE_RATE, DEFAULT_CENTER_FREQ, DEFAULT_BUFF_SIZE


class SDRController(QObject):
    iq_block = pyqtSignal(np.ndarray)
    new_iq_data = pyqtSignal(np.ndarray)     # flux IQ brut (si besoin)
    new_data    = pyqtSignal(np.ndarray)     # pour la constellation (IQ)
    center_frequency_changed = QtCore.pyqtSignal(float)
    sample_rate_about_to_change = QtCore.pyqtSignal(float)  # nouveau FS
    sample_rate_changed = QtCore.pyqtSignal(float)

    def __init__(self,
                 sample_rate=DEFAULT_SAMPLE_RATE,
                 center_freq=DEFAULT_CENTER_FREQ,
                 buff_size=DEFAULT_BUFF_SIZE):
        super().__init__()

        # État
        self.running = False
        self.thread = None
        self.stream = None
        self._last_stream_error_log = 0.0
        self._timeout_code = int(getattr(SoapySDR, "SOAPY_SDR_TIMEOUT", -1))
        self._last_plot_push = 0.0
        self._plot_interval_s = 1.0 / 20.0  # limiter l'UI spectre/waterfall à ~20 FPS

        # Réglages
        self.sample_rate = float(sample_rate)
        self.center_freq = float(center_freq)
        self.buff_size   = int(buff_size)
        self.fft_size    = int(buff_size)

        # Matériel / infos
        self.sdr = None
        self.hwinfo = {}

        # Data storage (spectre, etc.)
        self.data_storage = DataStorage(max_history_size=100)

        # Découverte et ouverture SDR (robuste)
        self._init_device()

        # Gains par défaut
        self.if_gain = 40
        self.rf_gain = 15
        self.agc     = False

        # Appliquer la config si HW présent
        if self.sdr is not None:
            self.sdr.setSampleRate(SOAPY_SDR_RX, 0, self.sample_rate)
            self.sdr.setFrequency(SOAPY_SDR_RX, 0, self.center_freq)

    # ---- Device init (robuste) ----
    def _init_device(self):
        self.hwinfo['devices'] = SoapySDR.Device_enumerate()
        try:
            self.sdr = SoapySDR.Device(dict(driver="sdrplay"))
        except Exception as e:
            self.sdr = None
            print(f"[WARN] No SDRPlay device: {e} — running in dummy mode.")

        if self.sdr is not None:
            # Infos réelles
            self.hwinfo['antennas']    = self.sdr.listAntennas(SOAPY_SDR_RX, 0)
            self.hwinfo['gainRange']   = self.sdr.getGainRange(SOAPY_SDR_RX, 0)
            self.hwinfo['sampleRates'] = self.sdr.listSampleRates(SOAPY_SDR_RX, 0)
        else:
            # Valeurs par défaut en dummy
            self.hwinfo['antennas']    = ["Antenna A", "Antenna B"]
            self.hwinfo['gainRange']   = None
            self.hwinfo['sampleRates'] = [self.sample_rate]

    # ---- Cycle de vie ----
    def start(self):
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self.run, daemon=True, name="SDR-Thread")
        self.thread.start()

    def stop(self):
        self.running = False
        if self.thread and self.thread.is_alive():
            if threading.current_thread() is not self.thread:
                try:
                    self.thread.join()
                except RuntimeError:
                    pass
        self.thread = None

    # ---- Boucle d’acquisition ----
    def run(self):
        try:
            if self.sdr is None:
                # ----- DUMMY MODE: génère IQ + spectre -----
                t = 0
                buffer = np.zeros(self.buff_size, dtype=np.complex64)
                while self.running:
                    n  = np.arange(self.buff_size, dtype=np.float32)
                    fs = float(self.sample_rate)
                    # deux tons + bruit
                    tone1 = np.exp(1j * 2*np.pi*(0.10*fs)*n/fs)
                    tone2 = np.exp(1j * 2*np.pi*(0.22*fs)*n/fs)
                    noise = 0.1 * (np.random.randn(self.buff_size) + 1j*np.random.randn(self.buff_size))
                    buffer = (0.5*tone1 + 0.3*tone2 + noise).astype(np.complex64)

                    self.iq_block.emit(buffer.copy())
                    now = time.monotonic()
                    if now - self._last_plot_push >= self._plot_interval_s:
                        power = self.compute_spectrum(buffer)
                        freqs = np.fft.fftshift(np.fft.fftfreq(len(power), 1 / fs)) + self.center_freq
                        self.data_storage.update({"timestamp": t, "x": freqs, "y": power})
                        self._last_plot_push = now

                    t += 1
                    time.sleep(0.01)
                return

            # ----- HARDWARE PATH -----
            self.sdr.setSampleRate(SOAPY_SDR_RX, 0, self.sample_rate)
            self.sdr.setFrequency(SOAPY_SDR_RX, 0, self.center_freq)
            self.sdr.setGainMode(SOAPY_SDR_RX, 0, False)
            self.sdr.setGain(SOAPY_SDR_RX, 0, 'IFGR', self.if_gain)
            self.sdr.setGain(SOAPY_SDR_RX, 0, 'RFGR', self.rf_gain)

            if self.stream is None:
                self.stream = self.sdr.setupStream(SOAPY_SDR_RX, SOAPY_SDR_CF32)
            # IMPORTANT: flags=0 pour lever toute ambiguïté d’overload
            self.sdr.activateStream(self.stream, 0)
            print(f"[SDR] HW stream activate: fs={self.sample_rate}, fc={self.center_freq}")

            buffer = np.zeros(self.buff_size, dtype=np.complex64)
            while self.running:
                sr = self.sdr.readStream(self.stream, [buffer], self.buff_size)
                if sr.ret > 0:
                    n_read = int(sr.ret)
                    iq = buffer[:n_read].copy()
                    self.iq_block.emit(iq)
                    now = time.monotonic()
                    if now - self._last_plot_push >= self._plot_interval_s:
                        power = self.compute_spectrum(iq)
                        fs = float(self.sample_rate)
                        freqs = np.fft.fftshift(np.fft.fftfreq(len(power), 1 / fs)) + self.center_freq
                        self.data_storage.update({"timestamp": now, "x": freqs, "y": power})
                        self._last_plot_push = now
                elif sr.ret == self._timeout_code:
                    time.sleep(0.001)
                elif sr.ret < 0:
                    # Limiter les logs d'erreur stream pour éviter le spam.
                    now = time.monotonic()
                    if now - self._last_stream_error_log >= 1.0:
                        print(f"[SDR] readStream error: ret={sr.ret}")
                        self._last_stream_error_log = now
                    time.sleep(0.001)

        except Exception as e:
            print(f"Erreur SDR : {e}")
        finally:
            # Fermeture propre du stream matériel
            if self.sdr is not None and self.stream is not None:
                try:
                    self.sdr.deactivateStream(self.stream)
                except Exception:
                    pass
                try:
                    self.sdr.closeStream(self.stream)
                except Exception:
                    pass
                self.stream = None

    # ---- Réglages ----
    def update_if_gain(self, value):
        self.if_gain = int(value)
        if self.sdr is not None:
            self.sdr.setGain(SOAPY_SDR_RX, 0, "IFGR", self.if_gain)

    def update_rf_gain(self, value):
        self.rf_gain = int(value)
        if self.sdr is not None:
            self.sdr.setGain(SOAPY_SDR_RX, 0, "RFGR", self.rf_gain)

    def update_agc(self, agc):
        self.agc = bool(agc)
        if self.sdr is not None:
            self.sdr.setGainMode(SOAPY_SDR_RX, 0, self.agc)

    def set_frequency(self, frequency):
        self.center_freq = float(frequency)
        if self.sdr is not None:
            self.sdr.setFrequency(SOAPY_SDR_RX, 0, self.center_freq)
        self.center_frequency_changed.emit(self.center_freq)

    def set_sample_rate(self, new_sample_rate):
        new_sample_rate = float(new_sample_rate)
        print(f"[SDR] FS change requested: {self.sample_rate} -> {new_sample_rate}")
        was_running = bool(self.running)

        # 1) prévenir tout le monde (RX/démod) AVANT d'arrêter le flux
        self.sample_rate_about_to_change.emit(new_sample_rate)

        # 2) stop acquisition (coupe net l’émission de blocs IQ)
        #    Attention à ne pas join sur soi-même si appelé depuis le thread SDR.
        if was_running and threading.current_thread() is self.thread:
            # on signale à la boucle de sortir; le restart se fera depuis le thread appelant
            self.running = False
        elif was_running:
            self.stop()

        # 3) appliquer côté HW
        self.sample_rate = new_sample_rate
        if self.sdr is not None:
            try:
                self.sdr.setSampleRate(SOAPY_SDR_RX, 0, self.sample_rate)
            except Exception as e:
                print(f"[SDR] setSampleRate error: {e}")

        # 4) signal “FS changé” (UI/Receiver)
        self.sample_rate_changed.emit(self.sample_rate)
        print(f"[SDR] FS applied & signal emitted: {self.sample_rate}")

        # 5) redémarrer proprement (si l'appel ne vient pas de la boucle SDR)
        if was_running and threading.current_thread() is not self.thread:
            self.start()

    def set_antenna(self, antenna):
        if not antenna:
            return
        self.antenna = antenna
        if self.sdr is not None:
            self.sdr.setAntenna(SOAPY_SDR_RX, 0, self.antenna)

    # ---- Spectre ----
    def compute_spectrum(self, iq_data):
        if len(iq_data) != self.fft_size:
            iq_data = np.pad(iq_data, (0, self.fft_size - len(iq_data)), mode='constant')
        fft_data = np.fft.fftshift(np.fft.fft(iq_data, self.fft_size))
        fft_data = self._ema_filter(fft_data, alpha=0.1)  # lissage léger
        power_spectrum = 20 * np.log10(np.abs(fft_data) + 1e-6)
        return power_spectrum

    @staticmethod
    def _ema_filter(data, alpha=0.2):
        return lfilter([alpha], [1, alpha - 1], data)
