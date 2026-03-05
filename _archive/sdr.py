import SoapySDR
from SoapySDR import SOAPY_SDR_RX, SOAPY_SDR_CF32
import numpy as np
import threading
import time
from PyQt5 import QtCore
from PyQt5.QtCore import QObject, pyqtSignal
from data import DataStorage
from scipy.signal import butter, filtfilt, lfilter
import numpy as np

class SDRController(QObject):
    new_iq_data = pyqtSignal(np.ndarray)  # 🚀 Envoie le flux IQ brut aux récepteurs
    new_data = QtCore.pyqtSignal(object)  # Signal pour envoyer les data
    center_frequency_changed = QtCore.pyqtSignal(float)
    history_updated = QtCore.pyqtSignal(object)

    def __init__(self, sample_rate=5e6, center_freq=392.025e6, buff_size=65536):
        super().__init__()
        self.running = False
        self.sample_rate = sample_rate
        self.center_freq = center_freq
        self.buff_size = buff_size
        self.fft_size = buff_size

        self.sdr = None


        self.hwinfo = {}
        self.hwinfo['devices'] = SoapySDR.Device_enumerate()

        # select device sdrplay
        args = dict(driver="sdrplay")
        self.sdr = SoapySDR.Device(args)

        self.data_storage = DataStorage(max_history_size=100)
        self.stream = self.sdr.setupStream(SOAPY_SDR_RX, SOAPY_SDR_CF32)
        self.thread = None

        # Get SDR information
        self.hwinfo['antennas'] = self.sdr.listAntennas(SOAPY_SDR_RX, 0)
        self.hwinfo['offset'] = self.sdr.getDCOffset(SOAPY_SDR_RX, 0)
        self.hwinfo['offsetMode'] = self.sdr.getDCOffsetMode(SOAPY_SDR_RX, 0)
        self.hwinfo['gain'] = self.sdr.getGain(SOAPY_SDR_RX, 0)
        self.hwinfo['gainMode'] = self.sdr.getGainMode(SOAPY_SDR_RX, 0)
        self.hwinfo['gainRange'] = self.sdr.getGainRange(SOAPY_SDR_RX, 0)
        self.hwinfo['hardwareInfo'] = self.sdr.getHardwareInfo()
        self.hwinfo['IQBalance'] = self.sdr.getIQBalance(SOAPY_SDR_RX, 0)
        self.hwinfo['IQBalanceMode'] = self.sdr.getIQBalanceMode(SOAPY_SDR_RX, 0)
        self.hwinfo['bandwidths'] = self.sdr.listBandwidths(SOAPY_SDR_RX, 0)
        self.hwinfo['sampleRates'] = self.sdr.listSampleRates(SOAPY_SDR_RX, 0)
        self.hwinfo['listFrequencies'] = self.sdr.listFrequencies(SOAPY_SDR_RX, 0)
        self.hwinfo['rfnotch_ctrl'] = self.sdr.readSetting("rfnotch_ctrl")
        self.hwinfo['dabnotch_ctrl'] =self.sdr.readSetting("dabnotch_ctrl")
        self.hwinfo['biasT_ctrl'] =self.sdr.readSetting("biasT_ctrl")
        self.hwinfo['iqcorr_ctrl'] = self.sdr.readSetting("iqcorr_ctrl")

        self.sdr.setSampleRate(SOAPY_SDR_RX, 0, self.sample_rate)
        self.sdr.setFrequency(SOAPY_SDR_RX, 0, self.center_freq)
        self.if_gain = 40
        self.rf_gain = 15
        self.agc = False
        print(self.sdr.getBandwidth(SOAPY_SDR_RX, 0))

    def start(self):
        """Lance la capture IQ"""
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self.run, daemon=True)
        self.thread.start()

    def stop(self):
        """Arrête la capture IQ"""
        self.running = False
        if self.thread:
            self.thread.join()

    def run(self):
        try:
            # Configure SDR
            self.sdr.setSampleRate(SOAPY_SDR_RX, 0, self.sample_rate)
            self.sdr.setFrequency(SOAPY_SDR_RX, 0, self.center_freq)
            self.sdr.setGainMode(SOAPY_SDR_RX, 0, False)
            self.sdr.setGain(SOAPY_SDR_RX, 0, 'IFGR', self.if_gain)
            self.sdr.setGain(SOAPY_SDR_RX, 0, 'RFGR', self.rf_gain)

            self.stream = self.sdr.setupStream(SOAPY_SDR_RX, SOAPY_SDR_CF32)
            self.sdr.activateStream(self.stream)
            buffer = np.zeros(self.buff_size, dtype=np.complex64)

            while self.running:
                sr = self.sdr.readStream(self.stream, [buffer], self.buff_size)

                if sr.ret > 0:
                    power = self.compute_spectrum(buffer)
                    freqs = np.fft.fftshift(np.fft.fftfreq(len(buffer), 1 / self.sample_rate))
                    freqs = (freqs + self.center_freq)
                    self.databuffer = {"timestamp": 0, "x": list(freqs), "y": list(power)}
                    self.data_storage.update(self.databuffer)


                    # Conversion en bande de base (décalage par rapport à la fréquence centrale)
                    # bw = 25e3  # Bande passante de 100 kHz
                    # nyquist = 0.5 * self.sample_rate  # Fréquence de Nyquist
                    # baseband_freq = (self.selected_freq - self.center_freq) / nyquist
                    # lowcut = 0.5 + (baseband_freq - (bw / nyquist))
                    # highcut = 0.5 + (baseband_freq + (bw / nyquist))
                    #
                    # # 🚨 Vérification avant de filtrer
                    # if not (0 < lowcut < highcut < 1):
                    #     print(f"🚨 ERREUR Filtrage : low={lowcut:.6f}, high={highcut:.6f}, Nyquist={nyquist}")


                    # filtered_data = self.bandpass_filter(buffer, lowcut, highcut, self.sample_rate)
                    # filtered_data = self.costas_loop(filtered_data, self.sample_rate)
                    # # iq_data = self.differential_decode(filtered_data)

                    # Envoyer aux plots
                    self.new_data.emit(buffer)
                time.sleep(0.01)

            self.sdr.deactivateStream(self.stream)
            self.sdr.closeStream(self.stream)

        except Exception as e:
            print(f"Erreur SDR : {e}")
            self.running = False

    def update_if_gain(self, value):
        """Met à jour le gain IF et applique la configuration au SDR"""
        self.if_gain = value
        if self.sdr is not None:
            self.sdr.setGain(SOAPY_SDR_RX, 0, "IFGR", self.if_gain)

    def update_rf_gain(self, value):
        """Met à jour le gain RF et applique la configuration au SDR"""
        self.rf_gain = value
        if self.sdr is not None:
            self.sdr.setGain(SOAPY_SDR_RX, 0, "RFGR", self.rf_gain)

    def update_agc(self, agc):
        self.agc = agc
        self.sdr.setGainMode(SOAPY_SDR_RX, 0, self.agc)

    def set_frequency(self, frequency):
        self.center_freq = frequency
        self.sdr.setFrequency(SOAPY_SDR_RX, 0, self.center_freq)
        self.center_frequency_changed.emit(self.center_freq)

    def set_sample_rate(self, new_sample_rate):
        self.sample_rate = new_sample_rate
        self.stop()
        self.sdr.setSampleRate(SOAPY_SDR_RX, 0, self.sample_rate)
        self.start()

    def set_fm_notch(self, fmnotch):
        self.sdr.writeSetting("rfnotch_ctrl", fmnotch)

    def set_dab_notch(self, dabnotch):
        self.sdr.writeSetting("dabnotch_ctrl", dabnotch)

    def set_bias_tee(self, biastee):
        self.sdr.writeSetting("biasT_ctrl", biastee)

    def set_antenna(self, antenna):
        if antenna is not None:
            self.antenna = antenna
            self.sdr.setAntenna(SOAPY_SDR_RX, 0, self.antenna)

    def set_iqctrl(self, iqcorr_ctrl):
        self.sdr.writeSetting("iqcorr_ctrl", iqcorr_ctrl)

    def update_frequency_axis(self):
        freqs = np.fft.fftshift(np.fft.fftfreq(self.buff_size, 1 / self.sample_rate))
        freqs = (freqs + self.center_freq)

    def compute_spectrum(self, iq_data):
        if len(iq_data) != self.fft_size:
            iq_data = np.pad(iq_data, (0, self.fft_size - len(iq_data)), mode='constant')

        fft_data = np.fft.fftshift(np.fft.fft(iq_data, self.fft_size))
        fft_data = self.lowpass_filter(fft_data, alpha=0.1)
        power_spectrum = 20 * np.log10(np.abs(fft_data) + 1e-6)
        return power_spectrum

    def lowpass_filter(self, data, alpha=0.2):
        return lfilter([alpha], [1, alpha - 1], data)



class Receiver(QObject):
    new_data = pyqtSignal(np.ndarray)  # 🚀 Signal pour envoyer les données traitées

    def __init__(self, controller, selected_freq, bandwidth=25e3):
        super().__init__()
        self.controller = controller
        self.selected_freq = selected_freq
        self.bandwidth = bandwidth
        self.sample_rate = controller.sample_rate

        self.controller.new_iq_data.connect(self.process_iq_data)

    def process_iq_data(self, iq_data):
        """Filtre et traite les données IQ"""
        nyquist = 0.5 * self.sample_rate
        baseband_freq = (self.selected_freq - self.controller.center_freq) / nyquist
        lowcut = 0.5 + (baseband_freq - (self.bandwidth / nyquist))
        highcut = 0.5 + (baseband_freq + (self.bandwidth / nyquist))

        # Vérification des bornes du filtre
        if not (0 < lowcut < 1 and 0 < highcut < 1):
            print(f"🚨 ERREUR Filtrage : low={lowcut:.6f}, high={highcut:.6f}")
            return

        filtered_data = self.bandpass_filter(iq_data, lowcut, highcut)
        self.new_data.emit(filtered_data)

    def bandpass_filter(self, data, lowcut, highcut, order=5):
        """Applique un filtre passe-bande"""
        b, a = butter(order, [lowcut, highcut], btype='band')
        return filtfilt(b, a, data)

    def set_selected_frequency(self, frequency):
        """Met à jour la fréquence sélectionnée par l'utilisateur"""
        self.selected_freq = frequency
        print(f"Fréquence sélectionnée mise à jour : {self.selected_freq} Hz")

    def set_bandwidth(self, bandwidth):
        """Met à jour la bande passante du filtre passe-bande."""
        self.bandwidth = bandwidth
        print(f"🔄 Bande passante mise à jour : {self.bandwidth} Hz")

    def costas_loop(self, iq_data, sample_rate, loop_bandwidth=0.01):
        """
        Implémentation d'une boucle de Costas pour la correction de fréquence et phase.

        Arguments :
        - iq_data : Signal IQ à corriger
        - sample_rate : Fréquence d'échantillonnage (Hz)
        - loop_bandwidth : Largeur de bande de la boucle de Costas (0.01 recommandé)

        Retourne :
        - iq_corrected : Signal corrigé
        """
        phase = 0.0
        freq = 0.0
        loop_gain = 2 * np.pi * loop_bandwidth / sample_rate  # Normalisation du gain
        iq_corrected = np.zeros_like(iq_data, dtype=complex)

        for i in range(len(iq_data)):
            iq_corrected[i] = iq_data[i] * np.exp(-1j * phase)
            error = np.angle(iq_corrected[i])  # Erreur de phase
            freq += loop_gain * error  # Ajustement normalisé de la fréquence
            phase += freq  # Mise à jour de la phase

        return iq_corrected
