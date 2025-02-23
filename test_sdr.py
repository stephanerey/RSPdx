import sys
import SoapySDR
from SoapySDR import *
import numpy as np
import matplotlib
matplotlib.use("Qt5Agg")
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import matplotlib.ticker as ticker
import logging
from PyQt5 import QtWidgets, QtCore
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas

# Configurer le logging
logging.basicConfig(
    filename="sdr_debug.log",
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

# Classe de réception SDR
class Receiver:
    def __init__(self):
        try:
            logger.info("Initializing SDRplay device...")
            self.sdr = SoapySDR.Device({"driver": "sdrplay"})
            logger.info("SDRplay device initialized successfully.")
            print(self.sdr.listGains(SOAPY_SDR_RX, 0))
            # Valeurs par défaut (en Hz)
            self.sample_rate = 1e6
            self.center_freq = 137.1e6
            self.IFgain = 30
            self.RFgain = 10
            # Par défaut, on désactive l'AGC (manual gain)
            self.agc = False
            self.update_settings(self.sample_rate, self.center_freq, self.IFgain, self.RFgain, self.agc)

            logger.info(f"Sample rate set to {self.sample_rate} Hz.")
            logger.info(f"Center frequency set to {self.center_freq} Hz.")
            logger.info(f"IF Gain set to {self.IFgain}.")
            logger.info(f"RF Gain set to {self.RFgain}.")

            # Setup du stream SDR
            self.rx_stream = self.sdr.setupStream(SOAPY_SDR_RX, SOAPY_SDR_CF32)
            self.sdr.activateStream(self.rx_stream)
            logger.info("Stream setup successfully.")
            logger.info("Streaming started.")
        except Exception as e:
            logger.error(f"Error initializing SDRplay device: {e}")
            exit(1)

        # Ces attributs seront assignés depuis l'interface pour la mise à jour des plots
        self.ax1 = None
        self.line = None
        self.waterfall = None
        self.waterfall_data = None

    def update_plot(self, iq_data):
        try:
            # Calcul de la FFT et application du décalage
            fft_data = np.fft.fft(iq_data)
            fft_data = np.fft.fftshift(fft_data)
            power = 20 * np.log10(np.abs(fft_data) + 1e-6)

            # Calcul des fréquences et recentrage autour de center_freq
            freqs = np.fft.fftfreq(len(iq_data), 1 / self.sample_rate)
            freqs = np.fft.fftshift(freqs)
            freqs += self.center_freq

            # Mise à jour du spectre
            self.line.set_data(freqs, power)
            self.ax1.set_xlim(freqs[0], freqs[-1])

            # Mise à jour du waterfall
            self.waterfall_data = np.roll(self.waterfall_data, -1, axis=0)
            self.waterfall_data[-1, :] = power
            self.waterfall.set_data(self.waterfall_data)
            self.waterfall.set_clim(-20, 0)
            self.waterfall.autoscale()

            return self.line, self.waterfall
        except Exception as e:
            logger.error(f"Error updating plot: {e}")

    def animate(self, i):
        try:
            expected_len = 1024
            buff = np.zeros(expected_len, np.complex64)
            sr = self.sdr.readStream(self.rx_stream, [buff], expected_len)
            if sr.ret > 0:
                # Si le nombre de samples retournés est inférieur à la taille attendue, on complète par des zéros
                if sr.ret < expected_len:
                    iq_data = np.zeros(expected_len, np.complex64)
                    iq_data[:sr.ret] = buff[:sr.ret]
                else:
                    iq_data = buff
                logger.debug(f"ReadStream returned {sr.ret} samples.")
                self.update_plot(iq_data)
            elif sr.ret == 0:
                logger.warning("No samples available (ret=0).")
            else:
                logger.error(f"Error reading samples: {sr.ret}")
        except Exception as e:
            logger.error(f"Error during streaming: {e}")

    def update_settings(self, sample_rate, center_freq, IFgain, RFgain, agc):
        try:
            self.sample_rate = sample_rate
            self.center_freq = center_freq
            self.IFgain = IFgain
            self.RFgain = RFgain

            # Désactiver ou activer l'AGC en fonction de la valeur booléenne agc
            self.sdr.setGainMode(SOAPY_SDR_RX, 0, agc)
            self.sdr.setSampleRate(SOAPY_SDR_RX, 0, self.sample_rate)
            self.sdr.setFrequency(SOAPY_SDR_RX, 0, self.center_freq)
            self.sdr.setGain(SOAPY_SDR_RX, 0, "IFGR", self.IFgain)
            self.sdr.setGain(SOAPY_SDR_RX, 0, "RFGR", self.RFgain)
            logger.info("Settings updated:")
            logger.info(f"Sample rate: {self.sample_rate} Hz, Center frequency: {self.center_freq} Hz, IF Gain: {self.IFgain}, RF Gain: {self.RFgain}, AGC: {agc}")
        except Exception as e:
            logger.error(f"Error updating settings: {e}")

# Interface principale PyQt
class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SDR Receiver")
        self.receiver = Receiver()
        self.init_ui()
        self.init_plot()
        self.start_animation()

    def init_ui(self):
        central_widget = QtWidgets.QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QtWidgets.QVBoxLayout(central_widget)

        # Panel de contrôle en haut
        control_layout = QtWidgets.QHBoxLayout()

        # Sample rate : dropdown (en MHz)
        sample_rate_label = QtWidgets.QLabel("Sample Rate (MHz):")
        self.sample_rate_combo = QtWidgets.QComboBox()
        for i in range(1, 11):  # Options de 1 à 10 MHz
            self.sample_rate_combo.addItem(str(i))
        self.sample_rate_combo.setCurrentText("1")
        control_layout.addWidget(sample_rate_label)
        control_layout.addWidget(self.sample_rate_combo)

        # Center frequency : textedit (en MHz)
        center_freq_label = QtWidgets.QLabel("Center Frequency (MHz):")
        self.center_freq_edit = QtWidgets.QLineEdit()
        self.center_freq_edit.setText("137.1")
        control_layout.addWidget(center_freq_label)
        control_layout.addWidget(self.center_freq_edit)

        # IF Gain : slider avec label de valeur
        IF_layout = QtWidgets.QHBoxLayout()
        IFgain_label = QtWidgets.QLabel("IF Gain:")
        self.IFgain_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.IFgain_slider.setRange(20, 59)
        self.IFgain_slider.setValue(30)
        self.IFgain_value_label = QtWidgets.QLabel(str(self.IFgain_slider.value()))
        self.IFgain_slider.valueChanged.connect(lambda val: self.IFgain_value_label.setText(str(val)))
        IF_layout.addWidget(IFgain_label)
        IF_layout.addWidget(self.IFgain_slider)
        IF_layout.addWidget(self.IFgain_value_label)
        control_layout.addLayout(IF_layout)

        # RF Gain : slider avec label de valeur
        RF_layout = QtWidgets.QHBoxLayout()
        RFgain_label = QtWidgets.QLabel("RF Gain:")
        self.RFgain_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.RFgain_slider.setRange(0, 9)
        self.RFgain_slider.setValue(10)
        self.RFgain_value_label = QtWidgets.QLabel(str(self.RFgain_slider.value()))
        self.RFgain_slider.valueChanged.connect(lambda val: self.RFgain_value_label.setText(str(val)))
        RF_layout.addWidget(RFgain_label)
        RF_layout.addWidget(self.RFgain_slider)
        RF_layout.addWidget(self.RFgain_value_label)
        control_layout.addLayout(RF_layout)

        # Case à cocher pour l'AGC
        self.agc_checkbox = QtWidgets.QCheckBox("Enable AGC")
        self.agc_checkbox.setChecked(False)
        control_layout.addWidget(self.agc_checkbox)
        self.agc_checkbox.toggled.connect(self.apply_settings)

        # Bouton pour appliquer les réglages (optionnel)
        self.apply_button = QtWidgets.QPushButton("Apply Settings")
        self.apply_button.clicked.connect(self.apply_settings)
        control_layout.addWidget(self.apply_button)

        main_layout.addLayout(control_layout)

        # Connexions pour mettre à jour automatiquement en fonction des modifications sur les widgets
        self.sample_rate_combo.currentIndexChanged.connect(self.apply_settings)
        self.center_freq_edit.editingFinished.connect(self.apply_settings)
        self.IFgain_slider.valueChanged.connect(self.apply_settings)
        self.RFgain_slider.valueChanged.connect(self.apply_settings)

        # Zone d'affichage Matplotlib (plots)
        self.figure, (self.ax1, self.ax2) = plt.subplots(2, 1, figsize=(10, 8))
        self.canvas = FigureCanvas(self.figure)
        main_layout.addWidget(self.canvas)

    def init_plot(self):
        # Formatter pour afficher en MHz
        formatter = ticker.FuncFormatter(lambda x, pos: f"{x/1e6:.1f}")

        # Plot du spectre (axe ax1)
        self.line, = self.ax1.plot([], [], color="blue", linewidth=0.5)
        self.ax1.set_ylim(-60, 40)
        self.ax1.set_title("Frequency Spectrum")
        self.ax1.set_xlabel("Frequency (MHz)")
        self.ax1.set_ylabel("Amplitude (dB)")
        self.ax1.xaxis.set_major_formatter(formatter)

        # Plot waterfall (axe ax2)
        # Création d'une matrice pour stocker les données du waterfall
        self.receiver.waterfall_data = np.zeros((1200, 1024))
        self.waterfall = self.ax2.imshow(
            self.receiver.waterfall_data,
            aspect="auto",
            extent=[self.receiver.center_freq - self.receiver.sample_rate / 2,
                    self.receiver.center_freq + self.receiver.sample_rate / 2,
                    0, 1200],
            cmap="jet",
            origin="lower",
            vmin=-40,  # Niveau minimum (couleur la plus « froide »)
            vmax=0  # Niveau maximum (couleur la plus « chaude »)
        )
        self.ax2.set_title("Waterfall Plot")
        self.ax2.set_xlabel("Frequency (MHz)")
        self.ax2.set_ylabel("Time (frames)")
        self.ax2.xaxis.set_major_formatter(formatter)

        # Transmettre les objets graphiques à l'instance receiver
        self.receiver.ax1 = self.ax1
        self.receiver.line = self.line
        self.receiver.waterfall = self.waterfall

    def start_animation(self):
        # Lancer l'animation qui appellera Receiver.animate périodiquement
        self.ani = animation.FuncAnimation(self.figure, self.receiver.animate, interval=50, cache_frame_data=False, blit=False)

    def apply_settings(self):
        try:
            # Récupérer et convertir les valeurs depuis les widgets
            sample_rate_mhz = float(self.sample_rate_combo.currentText())
            sample_rate = sample_rate_mhz * 1e6
            center_freq = float(self.center_freq_edit.text()) * 1e6
            IFgain = self.IFgain_slider.value()
            RFgain = self.RFgain_slider.value()
            agc = self.agc_checkbox.isChecked()

            # Mettre à jour les réglages du récepteur SDR
            self.receiver.update_settings(sample_rate, center_freq, IFgain, RFgain, agc)
            # Mise à jour des axes :
            # Pour le waterfall, on met à jour l'extent et les limites de l'axe
            self.waterfall.set_extent([center_freq - sample_rate / 2,
                                       center_freq + sample_rate / 2,
                                       0, 1200])
            self.ax2.set_xlim(center_freq - sample_rate / 2, center_freq + sample_rate / 2)
            # Pour le spectre, l'axe x sera mis à jour lors de l'update_plot via fftshift
            self.canvas.draw_idle()
        except Exception as e:
            logger.error(f"Error applying settings: {e}")

    def closeEvent(self, event):
        # Lors de la fermeture de l'application, nettoyer le stream SDR
        try:
            self.receiver.sdr.deactivateStream(self.receiver.rx_stream)
            self.receiver.sdr.closeStream(self.receiver.rx_stream)
            logger.info("Stream deactivated and closed.")
            logger.info("SDR device closed.")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
        event.accept()

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
