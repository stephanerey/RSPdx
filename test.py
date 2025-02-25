import sys
import numpy as np
import SoapySDR
from SoapySDR import *
import pyqtgraph as pg
from pyqtgraph.Qt import QtWidgets, QtCore, QtGui


class SDRReceiver:
    def __init__(self):
        self.sdr = SoapySDR.Device({"driver": "sdrplay"})
        self.sample_rate = 2e6
        self.center_freq = 137.1e6
        self.waterfall_size = 300  # Nombre de lignes du waterfall
        self.fft_size = 1024  # Taille de la FFT
        self.waterfall_data = np.zeros((self.waterfall_size, self.fft_size))

        self.rx_stream = self.sdr.setupStream(SOAPY_SDR_RX, SOAPY_SDR_CF32)
        self.sdr.activateStream(self.rx_stream)

    def read_samples(self):
        expected_len = 1024
        buff = np.zeros(self.fft_size, np.complex64)
        sr = self.sdr.readStream(self.rx_stream, [buff], self.fft_size)
        if sr.ret > 0:
            # Si le nombre de samples retournés est inférieur à la taille attendue, on complète par des zéros
            if sr.ret < expected_len:
                iq_data = np.zeros(expected_len, np.complex64)
                iq_data[:sr.ret] = buff[:sr.ret]
            else:
                iq_data = buff
                return iq_data

        return None

    def compute_spectrum(self, iq_data):
        if len(iq_data) != self.fft_size:
            iq_data = np.pad(iq_data, (0, self.fft_size - len(iq_data)), mode='constant')

        fft_data = np.fft.fftshift(np.fft.fft(iq_data, self.fft_size))
        power_spectrum = 20 * np.log10(np.abs(fft_data) + 1e-6)
        return power_spectrum


class SDRGUI(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.receiver = SDRReceiver()
        self.init_ui()

    def init_ui(self):
        layout = QtWidgets.QVBoxLayout(self)

        # Graphique du spectre
        self.spectrum_plot = pg.PlotWidget(title="Spectre")
        self.spectrum_curve = self.spectrum_plot.plot(pen="y")
        self.spectrum_plot.setLabel("left", "Amplitude (dB)")
        self.spectrum_plot.setLabel("bottom", "Fréquence (MHz)")
        layout.addWidget(self.spectrum_plot)

        # Graphique du waterfall
        self.waterfall_plot = pg.ImageView()
        self.waterfall_plot.ui.histogram.hide()  # Supprimer l'échelle dynamique
        self.waterfall_plot.ui.roiBtn.hide()
        self.waterfall_plot.ui.menuBtn.hide()
        layout.addWidget(self.waterfall_plot)

        # Ajout des sliders pour contrôler l'échelle du spectre
        self.ymin_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.ymin_slider.setRange(-100, 0)
        self.ymin_slider.setValue(-60)
        self.ymin_slider.valueChanged.connect(self.update_spectrum_limits)

        self.ymax_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.ymax_slider.setRange(0, 100)
        self.ymax_slider.setValue(40)
        self.ymax_slider.valueChanged.connect(self.update_spectrum_limits)

        slider_layout = QtWidgets.QHBoxLayout()
        slider_layout.addWidget(QtWidgets.QLabel("Ymin"))
        slider_layout.addWidget(self.ymin_slider)
        slider_layout.addWidget(QtWidgets.QLabel("Ymax"))
        slider_layout.addWidget(self.ymax_slider)
        layout.addLayout(slider_layout)

        # Ajout des contrôles pour la fréquence et l'échantillonnage
        control_layout = QtWidgets.QHBoxLayout()

        self.freq_input = QtWidgets.QLineEdit(str(self.receiver.center_freq / 1e6))
        self.freq_input.setValidator(QtGui.QDoubleValidator(10, 2000, 3))
        self.freq_input.editingFinished.connect(self.update_frequency)

        self.sample_rate_input = QtWidgets.QComboBox()
        for rate in [1, 2, 5, 10]:
            self.sample_rate_input.addItem(f"{rate} MHz", rate * 1e6)
        self.sample_rate_input.setCurrentIndex(1)
        self.sample_rate_input.currentIndexChanged.connect(self.update_sample_rate)

        control_layout.addWidget(QtWidgets.QLabel("Fréquence (MHz):"))
        control_layout.addWidget(self.freq_input)
        control_layout.addWidget(QtWidgets.QLabel("Sample Rate (MHz):"))
        control_layout.addWidget(self.sample_rate_input)

        layout.addLayout(control_layout)

        # Boutons Démarrer / Arrêter
        self.start_button = QtWidgets.QPushButton("Démarrer")
        self.start_button.clicked.connect(self.start_stream)

        self.stop_button = QtWidgets.QPushButton("Arrêter")
        self.stop_button.clicked.connect(self.stop_stream)
        self.stop_button.setEnabled(False)

        button_layout = QtWidgets.QHBoxLayout()
        button_layout.addWidget(self.start_button)
        button_layout.addWidget(self.stop_button)
        layout.addLayout(button_layout)

        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update_plot)

    def start_stream(self):
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.timer.start(50)

    def stop_stream(self):
        self.timer.stop()
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)

    def update_plot(self):
        iq_data = self.receiver.read_samples()
        if iq_data is not None:
            power_spectrum = self.receiver.compute_spectrum(iq_data)
            freqs = np.fft.fftshift(np.fft.fftfreq(len(iq_data), 1 / self.receiver.sample_rate))
            freqs += self.receiver.center_freq / 1e6  # Conversion en MHz

            ymin = self.ymin_slider.value()
            ymax = self.ymax_slider.value()
            self.spectrum_curve.setData(freqs, power_spectrum)
            self.spectrum_plot.setYRange(ymin, ymax)

            # **Défilement vertical du waterfall**
            self.receiver.waterfall_data[:-1] = self.receiver.waterfall_data[1:]
            self.receiver.waterfall_data[-1] = power_spectrum  # Nouvelle ligne ajoutée en bas

            # **Affichage du waterfall avec axes alignés**
            self.waterfall_plot.setImage(
                self.receiver.waterfall_data.T,
                autoLevels=False,
                levels=(-60, 40),
                autoRange=False
            )

            # Aligner les fréquences du waterfall avec le spectre
            self.waterfall_plot.view.setRange(
                xRange=(freqs[0], freqs[-1]),
                yRange=(0, self.receiver.waterfall_size)
            )

    def update_spectrum_limits(self):
        ymin = self.ymin_slider.value()
        ymax = self.ymax_slider.value()
        self.spectrum_plot.setYRange(ymin, ymax)

    def update_frequency(self):
        new_freq = float(self.freq_input.text()) * 1e6
        self.receiver.center_freq = new_freq
        self.receiver.sdr.setFrequency(SOAPY_SDR_RX, 0, new_freq)

    def update_sample_rate(self):
        new_rate = self.sample_rate_input.currentData()
        self.receiver.sample_rate = new_rate
        self.receiver.sdr.setSampleRate(SOAPY_SDR_RX, 0, new_rate)


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = SDRGUI()
    window.show()
    sys.exit(app.exec_())
