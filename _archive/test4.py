import sys
import SoapySDR
from SoapySDR import SOAPY_SDR_RX, SOAPY_SDR_CF32
import numpy as np
from PyQt5 import QtWidgets, QtCore, QtGui, uic
from scipy.signal import lfilter
import threading
import time
from plot import SpectrumPlotWidget, WaterfallPlotWidget, ConstellationPlotWidget
from data import DataStorage
from scipy.signal import butter, filtfilt


class SDRReceiver(QtCore.QObject):
    new_data = QtCore.pyqtSignal(object)  # Signal pour envoyer les data
    center_frequency_changed = QtCore.pyqtSignal(float)
    history_updated = QtCore.pyqtSignal(object)

    def __init__(self, sample_rate=5e6, center_freq=392.025e6, buff_size=65536):
        super().__init__()
        self.running = False
        self.sample_rate = sample_rate
        self.center_freq = center_freq
        self.selected_freq = self.center_freq  # Valeur par défaut = fréquence centrale

        self.buff_size = buff_size
        self.fft_size = buff_size
        self.sdr = None
        self.thread = None
        self.if_gain = 40
        self.rf_gain = 15
        self.agc = False
        self.data_storage = DataStorage(max_history_size=100)
        self.hwinfo = {}

        self.hwinfo['devices'] = SoapySDR.Device_enumerate()

        # select device sdrplay
        args = dict(driver="sdrplay")
        self.sdr = SoapySDR.Device(args)

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

        print(self.sdr.getBandwidth(SOAPY_SDR_RX, 0))

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
        # if self.running:
        #     self.sdr.deactivateStream(self.stream)  # Stop temporairement la capture
        #
        # self.sample_rate = new_sample_rate
        # self.sdr.setSampleRate(SOAPY_SDR_RX, 0, self.sample_rate)
        #
        # # Vidage des buffers pour éviter les artefacts
        # for _ in range(5):
        #     self.sdr.readStream(self.stream, [np.zeros(self.buff_size, dtype=np.complex64)], self.buff_size)
        #
        # if self.running:
        #     self.sdr.activateStream(self.stream)  # Relance la capture

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

    def start(self):
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self.run, daemon=True)
        self.thread.start()

    def stop(self):
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
                    bw = 25e3  # Bande passante de 100 kHz
                    nyquist = 0.5 * self.sample_rate  # Fréquence de Nyquist
                    baseband_freq = (self.selected_freq - self.center_freq) / nyquist
                    lowcut = 0.5 + (baseband_freq - (bw / nyquist))
                    highcut = 0.5 + (baseband_freq + (bw / nyquist))

                    # 🚨 Vérification avant de filtrer
                    if not (0 < lowcut < highcut < 1):
                        print(f"🚨 ERREUR Filtrage : low={lowcut:.6f}, high={highcut:.6f}, Nyquist={nyquist}")


                    filtered_data = self.bandpass_filter(buffer, lowcut, highcut, self.sample_rate)
                    filtered_data = self.costas_loop(filtered_data, self.sample_rate)
                    # iq_data = self.differential_decode(filtered_data)

                    # Envoyer aux plots
                    self.new_data.emit(filtered_data)
                time.sleep(0.01)

            self.sdr.deactivateStream(self.stream)
            self.sdr.closeStream(self.stream)

        except Exception as e:
            print(f"Erreur SDR : {e}")
            self.running = False

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

    import numpy as np

    def differential_decode(self, iq_data):
        """
        Effectue le décodage différentiel d'un signal IQ.

        Arguments :
        - iq_data : Signal complexe IQ sous forme de numpy.ndarray

        Retourne :
        - phases_diff : Phase différentiée du signal
        """
        if not isinstance(iq_data, np.ndarray):
            raise ValueError("iq_data doit être un tableau numpy.ndarray")

        # Extraire les parties réelles et imaginaires
        i = np.real(iq_data)
        q = np.imag(iq_data)

        # Vérifier que les données ne sont pas des entiers
        if np.issubdtype(i.dtype, np.integer) or np.issubdtype(q.dtype, np.integer):
            i = i.astype(np.float32)
            q = q.astype(np.float32)

        # Calculer la phase
        phases = np.arctan2(q, i)  # Assure-toi que `q` et `i` sont bien en float

        # Calculer la différence de phase (différentiation)
        phases_diff = np.diff(phases)

        return phases_diff

    def bandpass_filter(self, data, lowcut, highcut, fs, order=5):
        """Filtre passe-bande pour extraire une sous-bande du signal IQ"""
        nyquist = 0.5 * fs  # Fréquence de Nyquist

        # ✅ Les valeurs de lowcut et highcut sont déjà normalisées AVANT d'appeler cette fonction
        if not (0 < lowcut < 1 and 0 < highcut < 1):
            print(f"🚨 ERREUR Filtrage : low={lowcut}, high={highcut}, Nyquist={nyquist}")
            return data  # Retourne les données d'origine sans filtrage

        # Conception du filtre passe-bande
        b, a = butter(order, [lowcut, highcut], btype='band')

        # Application du filtre
        return filtfilt(b, a, data)

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


class SDRGUI(QtWidgets.QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        uic.loadUi('ui_main.ui', self)

        self.receiver = SDRReceiver()
        time.sleep(3)

        self.startButton.clicked.connect(self.start_sdr)
        self.stopButton.clicked.connect(self.stop_sdr)
        self.freqSpinBox_2.editingFinished.connect(self.update_frequency)
        self.sampleRateComboBox.currentIndexChanged.connect(self.update_sample_rate)
        self.antennaComboBox.currentIndexChanged.connect(self.set_antenna)
        self.IFGRHorizontalSlider.valueChanged.connect(self.update_ifgain)
        self.RFGRHorizontalSlider.valueChanged.connect(self.update_rfgain)
        self.AGCCheckBox.stateChanged.connect(self.set_agc)
        self.biasTeeCheckBox.stateChanged.connect(self.set_biastee)
        self.FMNotchCheckBox.stateChanged.connect(self.set_fmnotch)
        self.DABNotchCheckBox.stateChanged.connect(self.set_dabnotch)
        self.iqcrtlCheckBox.stateChanged.connect(self.set_iqctrl)

        # for device in self.receiver.hwinfo['devices']:
        #     self.sourceComboBox.addItem(device)
        for rate in self.receiver.hwinfo['sampleRates']:
            self.sampleRateComboBox.addItem(f"{rate / 1e6} MHz", rate)  # Display in MHz, store in Hz
        for antenna in self.receiver.hwinfo['antennas']:
            self.antennaComboBox.addItem(antenna)  # Display in MHz, store in Hz

        # Create plot widgets and update UI
        self.spectrumPlotWidget = SpectrumPlotWidget(self.mainPlotLayout, center_freq=self.receiver.center_freq)
        self.spectrumPlotWidget.receiver_frequency_changed.connect(self.receiver.set_selected_frequency)
        self.spectrumPlotWidget.receiver_bandwidth_changed.connect(self.receiver.set_bandwidth)

        self.receiver.center_frequency_changed.connect(self.spectrumPlotWidget.update_center_frequency)
        self.receiver.center_frequency_changed.connect(self.spectrumPlotWidget.update_selected_freq_line)

        self.waterfallPlotWidget = WaterfallPlotWidget(self.waterfallPlotLayout, self.histogramPlotLayout)
        self.constellationPlotWidget = ConstellationPlotWidget(self.constellationPlotLayout)
        self.receiver.new_data.connect(self.constellationPlotWidget.update_plot)

        self.receiver.data_storage.data_updated.connect(self.spectrumPlotWidget.update_plot)
        self.receiver.data_storage.data_updated.connect(self.spectrumPlotWidget.update_persistence)
        self.receiver.data_storage.data_recalculated.connect(self.spectrumPlotWidget.recalculate_plot)
        self.receiver.data_storage.data_recalculated.connect(self.spectrumPlotWidget.recalculate_persistence)
        self.receiver.data_storage.history_updated.connect(self.waterfallPlotWidget.update_plot)
        self.receiver.data_storage.history_recalculated.connect(self.waterfallPlotWidget.recalculate_plot)
        self.receiver.data_storage.average_updated.connect(self.spectrumPlotWidget.update_average)
        self.receiver.data_storage.baseline_updated.connect(self.spectrumPlotWidget.update_baseline)
        self.receiver.data_storage.peak_hold_max_updated.connect(self.spectrumPlotWidget.update_peak_hold_max)
        self.receiver.data_storage.peak_hold_min_updated.connect(self.spectrumPlotWidget.update_peak_hold_min)

        # Link main spectrum plot to waterfall plot
        self.spectrumPlotWidget.plot.setXLink(self.waterfallPlotWidget.plot)

        self.spectrumPlotWidget.main_curve = bool(self.mainCurveCheckBox.isChecked())
        # self.spectrumPlotWidget.main_color = str_to_color(("main_color", "255, 255, 0, 255"))
        self.spectrumPlotWidget.peak_hold_max = bool(self.peakHoldMaxCheckBox.isChecked())
        # self.spectrumPlotWidget.peak_hold_max_color = str_to_color(("peak_hold_max_color", "255, 0, 0, 255"))
        self.spectrumPlotWidget.peak_hold_min = bool(self.peakHoldMinCheckBox.isChecked())
        # self.spectrumPlotWidget.peak_hold_min_color = str_to_color(("peak_hold_min_color", "0, 0, 255, 255"))
        self.spectrumPlotWidget.average = bool(self.averageCheckBox.isChecked())
        # self.spectrumPlotWidget.average_color = str_to_color(("average_color", "0, 255, 255, 255"))
        self.spectrumPlotWidget.baseline = bool(self.baselineCheckBox.isChecked())
        # self.spectrumPlotWidget.baseline_color = str_to_color(("baseline_color", "255, 0, 255, 255"))
        self.spectrumPlotWidget.persistence = bool(self.persistenceCheckBox.isChecked())
        self.spectrumPlotWidget.persistence_length = ("persistence_length", 5, int)
        self.spectrumPlotWidget.persistence_decay = ("persistence_decay", "exponential")
        # self.spectrumPlotWidget.persistence_color = str_to_color(("persistence_color", "0, 255, 0, 255"))
        self.spectrumPlotWidget.clear_plot()
        self.spectrumPlotWidget.clear_peak_hold_max()
        self.spectrumPlotWidget.clear_peak_hold_min()
        self.spectrumPlotWidget.clear_average()
        self.spectrumPlotWidget.clear_baseline()
        # self.spectrumPlotWidget.clear_persistence()

    def start_sdr(self):
        self.startButton.setEnabled(False)
        self.stopButton.setEnabled(True)
        self.receiver.start()

    def stop_sdr(self):
        self.receiver.stop()
        self.startButton.setEnabled(True)
        self.stopButton.setEnabled(False)

    def update_spectrum_limits(self):
        ymin = self.ymin_slider.value()
        ymax = self.ymax_slider.value()
        self.spectrum_plot.setYRange(ymin, ymax)

    def update_frequency(self):
        new_freq = float(self.freqSpinBox_2.value()) * 1e6
        self.receiver.set_frequency(new_freq)
#        self.receiver.update_frequency_axis()

    def update_sample_rate(self):
        new_rate = self.sampleRateComboBox.currentData()
        self.receiver.set_sample_rate(new_rate)

    def set_antenna(self):
        antenna = self.antennaComboBox.currentText()
        self.receiver.set_antenna(antenna)
        if antenna == "Antenna B":
            self.biasTeeCheckBox.setEnabled(True)
        else:
            self.biasTeeCheckBox.setEnabled(False)

    def update_ifgain(self):
        new_ifgain = self.IFGRHorizontalSlider.value()
        self.receiver.update_if_gain(new_ifgain)

    def update_rfgain(self):
        new_rfgain = self.RFGRHorizontalSlider.value()
        self.receiver.update_rf_gain(new_rfgain)

    def set_agc(self):
        agc = True if self.AGCCheckBox.isChecked() is True else False
        self.receiver.update_agc(agc)
        if agc is True:
            self.IFGRHorizontalSlider.setEnabled(False)
        else:
            self.IFGRHorizontalSlider.setEnabled(True)
            self.update_ifgain()

    def set_iqctrl(self):
        iqctrl = 'true' if self.iqcrtlCheckBox.isChecked() is True else 'false'
        self.receiver.set_iqctrl(iqctrl)

    def set_biastee(self):
        biastee = 'true' if self.biasTeeCheckBox.isChecked() is True else 'false'
        self.receiver.set_bias_tee(biastee)

    def set_fmnotch(self):
        fmnotch = 'true' if self.FMNotchCheckBox.isChecked() is True else 'false'
        self.receiver.set_fm_notch(fmnotch)

    def set_dabnotch(self):
        dabnotch = 'true' if self.DABNotchCheckBox.isChecked() is True else 'false'
        self.receiver.set_dab_notch(dabnotch)


    def update_frequencyCorrection(self):
        pass

    @QtCore.pyqtSlot(bool)
    def on_mainCurveCheckBox_toggled(self, checked):
        self.spectrumPlotWidget.main_curve = checked
        if self.spectrumPlotWidget.curve.xData is None:
            self.spectrumPlotWidget.update_plot(self.receiver.data_storage)
        self.spectrumPlotWidget.curve.setVisible(checked)

    @QtCore.pyqtSlot(bool)
    def on_peakHoldMaxCheckBox_toggled(self, checked):
        self.spectrumPlotWidget.peak_hold_max = checked
        if self.spectrumPlotWidget.curve_peak_hold_max.xData is None:
            self.spectrumPlotWidget.update_peak_hold_max(self.receiver.data_storage)
        self.spectrumPlotWidget.curve_peak_hold_max.setVisible(checked)

    @QtCore.pyqtSlot(bool)
    def on_peakHoldMinCheckBox_toggled(self, checked):
        self.spectrumPlotWidget.peak_hold_min = checked
        if self.spectrumPlotWidget.curve_peak_hold_min.xData is None:
            self.spectrumPlotWidget.update_peak_hold_min(self.receiver.data_storage)
        self.spectrumPlotWidget.curve_peak_hold_min.setVisible(checked)

    @QtCore.pyqtSlot(bool)
    def on_averageCheckBox_toggled(self, checked):
        self.spectrumPlotWidget.average = checked
        if self.spectrumPlotWidget.curve_average.xData is None:
            self.spectrumPlotWidget.update_average(self.receiver.data_storage)
        self.spectrumPlotWidget.curve_average.setVisible(checked)

    @QtCore.pyqtSlot(bool)
    def on_persistenceCheckBox_toggled(self, checked):
        self.spectrumPlotWidget.persistence = checked
        if self.spectrumPlotWidget.persistence_curves[0].xData is None:
            self.spectrumPlotWidget.recalculate_persistence(self.receiver.data_storage)
        for curve in self.spectrumPlotWidget.persistence_curves:
            curve.setVisible(checked)

    @QtCore.pyqtSlot(bool)
    def on_smoothCheckBox_toggled(self, checked):
        settings = QtCore.QSettings()
        self.receiver.data_storage.set_smooth(
            checked,
            settings.value("smooth_length", 11, int),
            settings.value("smooth_window", "hanning")
        )

    @QtCore.pyqtSlot(bool)
    def on_baselineCheckBox_toggled(self, checked):
        self.spectrumPlotWidget.baseline = checked
        if self.spectrumPlotWidget.curve_baseline.xData is None:
            self.spectrumPlotWidget.update_baseline(self.receiver.data_storage)
        self.spectrumPlotWidget.curve_baseline.setVisible(checked)

    @QtCore.pyqtSlot(bool)
    def on_subtractBaselineCheckBox_toggled(self, checked):
        settings = QtCore.QSettings()
        self.receiver.data_storage.set_subtract_baseline(
            checked,
            settings.value("baseline_file", None)
        )

    # @QtCore.Slot()
    # def on_baselineButton_clicked(self):
    #     dialog = QSpectrumAnalyzerBaseline(self)
    #     if dialog.exec_():
    #         settings = QtCore.QSettings()
    #         self.data_storage.set_subtract_baseline(
    #             bool(self.subtractBaselineCheckBox.isChecked()),
    #             settings.value("baseline_file", None)
    #         )
    #
    # @QtCore.Slot()
    # def on_smoothButton_clicked(self):
    #     dialog = QSpectrumAnalyzerSmoothing(self)
    #     if dialog.exec_():
    #         settings = QtCore.QSettings()
    #         self.data_storage.set_smooth(
    #             bool(self.smoothCheckBox.isChecked()),
    #             settings.value("smooth_length", 11, int),
    #             settings.value("smooth_window", "hanning")
    #         )
    #
    # @QtCore.Slot()
    # def on_persistenceButton_clicked(self):
    #     prev_persistence_length = self.spectrumPlotWidget.persistence_length
    #     dialog = QSpectrumAnalyzerPersistence(self)
    #     if dialog.exec_():
    #         settings = QtCore.QSettings()
    #         persistence_length = settings.value("persistence_length", 5, int)
    #         self.spectrumPlotWidget.persistence_length = persistence_length
    #         self.spectrumPlotWidget.persistence_decay = settings.value("persistence_decay", "exponential")
    #
    #         # If only decay function has been changed, just reset colors
    #         if persistence_length == prev_persistence_length:
    #             self.spectrumPlotWidget.set_colors()
    #         else:
    #             self.spectrumPlotWidget.recalculate_persistence(self.data_storage)
    #
    # @QtCore.Slot()
    # def on_colorsButton_clicked(self):
    #     dialog = QSpectrumAnalyzerColors(self)
    #     if dialog.exec_():
    #         settings = QtCore.QSettings()
    #         self.spectrumPlotWidget.main_color = str_to_color(settings.value("main_color", "255, 255, 0, 255"))
    #         self.spectrumPlotWidget.peak_hold_max_color = str_to_color(
    #             settings.value("peak_hold_max_color", "255, 0, 0, 255"))
    #         self.spectrumPlotWidget.peak_hold_min_color = str_to_color(
    #             settings.value("peak_hold_min_color", "0, 0, 255, 255"))
    #         self.spectrumPlotWidget.average_color = str_to_color(settings.value("average_color", "0, 255, 255, 255"))
    #         self.spectrumPlotWidget.persistence_color = str_to_color(
    #             settings.value("persistence_color", "0, 255, 0, 255"))
    #         self.spectrumPlotWidget.baseline_color = str_to_color(settings.value("baseline_color", "255, 0, 255, 255"))
    #         self.spectrumPlotWidget.set_colors()

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = SDRGUI()
    window.show()
    sys.exit(app.exec_())
