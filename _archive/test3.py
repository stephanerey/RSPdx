import sys
from PyQt5 import QtWidgets, QtCore, QtGui, uic
import time
from plot import SpectrumPlotWidget, WaterfallPlotWidget, ConstellationPlotWidget
from sdr import SDRController, Receiver



class SDRGUI(QtWidgets.QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        uic.loadUi('ui_main.ui', self)

        self.controller = SDRController()
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
        for rate in self.controller.hwinfo['sampleRates']:
            self.sampleRateComboBox.addItem(f"{rate / 1e6} MHz", rate)  # Display in MHz, store in Hz
        for antenna in self.controller.hwinfo['antennas']:
            self.antennaComboBox.addItem(antenna)  # Display in MHz, store in Hz

        # Create plot widgets and update UI
        self.spectrumPlotWidget = SpectrumPlotWidget(self.mainPlotLayout, center_freq=self.controller.center_freq)
        # self.spectrumPlotWidget.receiver_frequency_changed.connect(self.controller.set_selected_frequency)
        # self.spectrumPlotWidget.receiver_bandwidth_changed.connect(self.controller.set_bandwidth)

        self.controller.center_frequency_changed.connect(self.spectrumPlotWidget.update_center_frequency)
        self.controller.center_frequency_changed.connect(self.spectrumPlotWidget.update_selected_freq_line)

        self.waterfallPlotWidget = WaterfallPlotWidget(self.waterfallPlotLayout, self.histogramPlotLayout)
        self.constellationPlotWidget = ConstellationPlotWidget(self.constellationPlotLayout)
        self.controller.new_data.connect(self.constellationPlotWidget.update_plot)

        self.controller.data_storage.data_updated.connect(self.spectrumPlotWidget.update_plot)
        self.controller.data_storage.data_updated.connect(self.spectrumPlotWidget.update_persistence)
        self.controller.data_storage.data_recalculated.connect(self.spectrumPlotWidget.recalculate_plot)
        self.controller.data_storage.data_recalculated.connect(self.spectrumPlotWidget.recalculate_persistence)
        self.controller.data_storage.history_updated.connect(self.waterfallPlotWidget.update_plot)
        self.controller.data_storage.history_recalculated.connect(self.waterfallPlotWidget.recalculate_plot)
        self.controller.data_storage.average_updated.connect(self.spectrumPlotWidget.update_average)
        self.controller.data_storage.baseline_updated.connect(self.spectrumPlotWidget.update_baseline)
        self.controller.data_storage.peak_hold_max_updated.connect(self.spectrumPlotWidget.update_peak_hold_max)
        self.controller.data_storage.peak_hold_min_updated.connect(self.spectrumPlotWidget.update_peak_hold_min)

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
        self.controller.start()

    def stop_sdr(self):
        self.controller.stop()
        self.startButton.setEnabled(True)
        self.stopButton.setEnabled(False)

    def update_spectrum_limits(self):
        ymin = self.ymin_slider.value()
        ymax = self.ymax_slider.value()
        self.spectrum_plot.setYRange(ymin, ymax)

    def update_frequency(self):
        new_freq = float(self.freqSpinBox_2.value()) * 1e6
        self.controller.set_frequency(new_freq)
#        self.receiver.update_frequency_axis()

    def update_sample_rate(self):
        new_rate = self.sampleRateComboBox.currentData()
        self.controller.set_sample_rate(new_rate)

    def set_antenna(self):
        antenna = self.antennaComboBox.currentText()
        self.controller.set_antenna(antenna)
        if antenna == "Antenna B":
            self.biasTeeCheckBox.setEnabled(True)
        else:
            self.biasTeeCheckBox.setEnabled(False)

    def update_ifgain(self):
        new_ifgain = self.IFGRHorizontalSlider.value()
        self.controller.update_if_gain(new_ifgain)

    def update_rfgain(self):
        new_rfgain = self.RFGRHorizontalSlider.value()
        self.controller.update_rf_gain(new_rfgain)

    def set_agc(self):
        agc = True if self.AGCCheckBox.isChecked() is True else False
        self.controller.update_agc(agc)
        if agc is True:
            self.IFGRHorizontalSlider.setEnabled(False)
        else:
            self.IFGRHorizontalSlider.setEnabled(True)
            self.update_ifgain()

    def set_iqctrl(self):
        iqctrl = 'true' if self.iqcrtlCheckBox.isChecked() is True else 'false'
        self.controller.set_iqctrl(iqctrl)

    def set_biastee(self):
        biastee = 'true' if self.biasTeeCheckBox.isChecked() is True else 'false'
        self.controller.set_bias_tee(biastee)

    def set_fmnotch(self):
        fmnotch = 'true' if self.FMNotchCheckBox.isChecked() is True else 'false'
        self.controller.set_fm_notch(fmnotch)

    def set_dabnotch(self):
        dabnotch = 'true' if self.DABNotchCheckBox.isChecked() is True else 'false'
        self.controller.set_dab_notch(dabnotch)

    def update_frequencyCorrection(self):
        pass

    @QtCore.pyqtSlot(bool)
    def on_mainCurveCheckBox_toggled(self, checked):
        self.spectrumPlotWidget.main_curve = checked
        if self.spectrumPlotWidget.curve.xData is None:
            self.spectrumPlotWidget.update_plot(self.controller.data_storage)
        self.spectrumPlotWidget.curve.setVisible(checked)

    @QtCore.pyqtSlot(bool)
    def on_peakHoldMaxCheckBox_toggled(self, checked):
        self.spectrumPlotWidget.peak_hold_max = checked
        if self.spectrumPlotWidget.curve_peak_hold_max.xData is None:
            self.spectrumPlotWidget.update_peak_hold_max(self.controller.data_storage)
        self.spectrumPlotWidget.curve_peak_hold_max.setVisible(checked)

    @QtCore.pyqtSlot(bool)
    def on_peakHoldMinCheckBox_toggled(self, checked):
        self.spectrumPlotWidget.peak_hold_min = checked
        if self.spectrumPlotWidget.curve_peak_hold_min.xData is None:
            self.spectrumPlotWidget.update_peak_hold_min(self.controller.data_storage)
        self.spectrumPlotWidget.curve_peak_hold_min.setVisible(checked)

    @QtCore.pyqtSlot(bool)
    def on_averageCheckBox_toggled(self, checked):
        self.spectrumPlotWidget.average = checked
        if self.spectrumPlotWidget.curve_average.xData is None:
            self.spectrumPlotWidget.update_average(self.controller.data_storage)
        self.spectrumPlotWidget.curve_average.setVisible(checked)

    @QtCore.pyqtSlot(bool)
    def on_persistenceCheckBox_toggled(self, checked):
        self.spectrumPlotWidget.persistence = checked
        if self.spectrumPlotWidget.persistence_curves[0].xData is None:
            self.spectrumPlotWidget.recalculate_persistence(self.controller.data_storage)
        for curve in self.spectrumPlotWidget.persistence_curves:
            curve.setVisible(checked)

    @QtCore.pyqtSlot(bool)
    def on_smoothCheckBox_toggled(self, checked):
        settings = QtCore.QSettings()
        self.controller.data_storage.set_smooth(
            checked,
            settings.value("smooth_length", 11, int),
            settings.value("smooth_window", "hanning")
        )

    @QtCore.pyqtSlot(bool)
    def on_baselineCheckBox_toggled(self, checked):
        self.spectrumPlotWidget.baseline = checked
        if self.spectrumPlotWidget.curve_baseline.xData is None:
            self.spectrumPlotWidget.update_baseline(self.controller.data_storage)
        self.spectrumPlotWidget.curve_baseline.setVisible(checked)

    @QtCore.pyqtSlot(bool)
    def on_subtractBaselineCheckBox_toggled(self, checked):
        settings = QtCore.QSettings()
        self.controller.data_storage.set_subtract_baseline(
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
