# src/gui/receiver_tab.py
from PyQt5 import QtWidgets, QtCore
from src.core.demodulators.fm import FMDemodulator, FMAudioMode
import sounddevice as sd

class ReceiverTab(QtWidgets.QWidget):
    """
    Panneau Receiver + section Audio (FM).
    """
    def __init__(self, parent=None):
        super().__init__(parent)

        form = QtWidgets.QFormLayout(self)

        # --- réglages RF ---
        self.freqSpin = QtWidgets.QDoubleSpinBox()
        self.freqSpin.setDecimals(6)
        self.freqSpin.setRange(0.0, 6000.0)
        self.freqSpin.setSuffix(" MHz")
        self.freqSpin.setSingleStep(0.001)

        self.bwSpin = QtWidgets.QDoubleSpinBox()
        self.bwSpin.setDecimals(1)
        self.bwSpin.setRange(0.1, 5000.0)
        self.bwSpin.setSuffix(" kHz")
        self.bwSpin.setSingleStep(0.1)

        self.costasEnable = QtWidgets.QCheckBox("Enable Costas loop")
        self.costasMode = QtWidgets.QComboBox(); self.costasMode.addItems(["qpsk", "bpsk"])
        self.iqCorrEnable = QtWidgets.QCheckBox("IQ correction")
        self.iqCorrEnable.setChecked(True)
        self.profileCombo = QtWidgets.QComboBox()
        self.profileCombo.addItem("Generic", "generic")
        self.profileCombo.addItem("TETRA", "tetra")
        self.constMode = QtWidgets.QComboBox()
        self.constMode.addItem("Raw IQ", "raw")
        self.constMode.addItem("Symbols", "symbols")
        self.constDomain = QtWidgets.QComboBox()
        self.constDomain.addItem("I/Q", "iq")
        self.constDomain.addItem("Differential", "differential")
        self.symbolRateSpin = QtWidgets.QDoubleSpinBox()
        self.symbolRateSpin.setDecimals(3)
        self.symbolRateSpin.setRange(0.001, 5000.0)
        self.symbolRateSpin.setSuffix(" ksym/s")
        self.symbolRateSpin.setSingleStep(0.001)
        self.symbolRateSpin.setValue(18.000)
        self.syncLabel = QtWidgets.QLabel("Sync: -- | EVM: --")
        self.syncLabel.setStyleSheet("color: #cccccc;")
        self.syncLabel.setWordWrap(True)

        form.addRow("Selected frequency:", self.freqSpin)
        form.addRow("Bandwidth:", self.bwSpin)
        form.addRow(self.costasEnable)
        form.addRow("Costas mode:", self.costasMode)
        form.addRow(self.iqCorrEnable)
        form.addRow("Profile:", self.profileCombo)
        form.addRow("Constellation:", self.constMode)
        form.addRow("Constellation domain:", self.constDomain)
        form.addRow("Symbol rate:", self.symbolRateSpin)
        form.addRow("Constellation quality:", self.syncLabel)

        # --- Audio FM ---
        sep = QtWidgets.QLabel("<b>Audio (FM)</b>")
        form.addRow(sep)

        self.fmEnable = QtWidgets.QCheckBox("FM audio")
        self.audioDevice = QtWidgets.QComboBox()
        self.refreshBtn = QtWidgets.QPushButton("↻")

        h = QtWidgets.QHBoxLayout()
        h.addWidget(self.audioDevice, 1)
        h.addWidget(self.refreshBtn, 0)
        form.addRow("Output device:", h)
        form.addRow(self.fmEnable)

        # état
        self._rx = None
        self._spec = None
        self._guard = False

        # signals RF
        self.freqSpin.valueChanged.connect(self._on_ui_freq_changed)
        self.bwSpin.valueChanged.connect(self._on_ui_bw_changed)
        self.costasEnable.toggled.connect(self._on_costas_toggled)
        self.costasMode.currentTextChanged.connect(self._on_costas_mode)
        self.iqCorrEnable.toggled.connect(self._on_iqcorr_toggled)
        self.profileCombo.currentIndexChanged.connect(self._on_profile_changed)
        self.constMode.currentIndexChanged.connect(self._on_const_mode_changed)
        self.constDomain.currentIndexChanged.connect(self._on_const_domain_changed)
        self.symbolRateSpin.valueChanged.connect(self._on_symbol_rate_changed)

        # signals audio
        self.fmEnable.toggled.connect(self._on_fm_toggled)
        self.audioDevice.currentIndexChanged.connect(self._on_device_changed)
        self.refreshBtn.clicked.connect(self._populate_devices)

    def _populate_devices(self):
        self.audioDevice.blockSignals(True)
        try:
            self.audioDevice.clear()
            devices = FMDemodulator.list_output_devices()
            for idx, name in devices:
                self.audioDevice.addItem(name, idx)

            # device de sortie par défaut si possible
            default_out = None
            try:
                default_out = sd.default.device[1]  # (in, out)
            except Exception:
                pass

            if default_out is not None:
                for i in range(self.audioDevice.count()):
                    if self.audioDevice.itemData(i) == default_out:
                        self.audioDevice.setCurrentIndex(i)
                        break
            elif self.audioDevice.count() > 0:
                self.audioDevice.setCurrentIndex(0)
        finally:
            self.audioDevice.blockSignals(False)

    # — binding —
    def bind(self, rx, spectrum_widget):
        self._rx = rx
        self._spec = spectrum_widget

        # instancie le demod si absent
        if getattr(rx, "demod", None) is None:
            rx.demod = FMDemodulator(
                audio_rate=48_000,
                deemph_us=50.0,  # 50 µs pour WFM (Europe) ; pour NFM c'est ignoré
                mode=FMAudioMode.NARROW  # ou FMAudioMode.WIDE suivant ton usage
            )

        self._populate_devices()

        # démarre l’audio par défaut
        try:
            # informe le démod du FS courant (au cas où)
            if getattr(rx, "demod", None) is not None:
                rx.demod.set_input_rate(getattr(rx, "_fs_bb", rx.sample_rate))
        except Exception:
            pass

        # coche la case et lance la sortie audio sur le device sélectionné
        self.fmEnable.setChecked(True)  # déclenche _on_fm_toggled -> start()
        self._guard = True
        try:
            self.freqSpin.setValue(rx.selected_freq / 1e6)
            self.bwSpin.setValue(rx.bandwidth / 1e3)
            self.costasEnable.setChecked(getattr(rx, "enable_costas", False))
            self.costasMode.setCurrentText(getattr(rx, "costas_mode", "qpsk"))
            self.iqCorrEnable.setChecked(bool(getattr(rx, "iq_correction_enabled", True)))
            prof = str(getattr(rx, "modulation_profile", "generic")).lower()
            idx_p = self.profileCombo.findData(prof)
            self.profileCombo.setCurrentIndex(idx_p if idx_p >= 0 else 0)
            mode = str(getattr(rx, "constellation_mode", "raw")).lower()
            idx = self.constMode.findData(mode)
            self.constMode.setCurrentIndex(idx if idx >= 0 else 0)
            domain = str(getattr(rx, "constellation_domain", "iq")).lower()
            idx_d = self.constDomain.findData(domain)
            self.constDomain.setCurrentIndex(idx_d if idx_d >= 0 else 0)
            self.symbolRateSpin.setValue(float(getattr(rx, "symbol_rate", 18_000.0)) / 1e3)
        finally:
            self._guard = False

        rx.frequency_changed.connect(self._on_rx_freq_changed)
        rx.bandwidth_changed.connect(self._on_rx_bw_changed)
        try:
            rx.quality_updated.connect(self._on_quality_updated)
        except Exception:
            pass

        spectrum_widget.receiver_frequency_changed.connect(self._on_spec_freq_changed)
        spectrum_widget.receiver_bandwidth_changed.connect(self._on_spec_bw_changed)

    # — UI → RX —
    def _on_ui_freq_changed(self, mhz: float):
        if self._guard or self._rx is None:
            return
        self._rx.set_selected_frequency(mhz * 1e6)

    def _on_ui_bw_changed(self, khz: float):
        if self._guard or self._rx is None:
            return
        self._rx.set_bandwidth(khz * 1e3)

    def _on_costas_toggled(self, checked: bool):
        if self._rx is None: return
        if hasattr(self._rx, "set_costas_enabled"):
            self._rx.set_costas_enabled(bool(checked))
        else:
            self._rx.enable_costas = bool(checked)

    def _on_costas_mode(self, text: str):
        if self._rx is None: return
        if hasattr(self._rx, "set_costas_mode"):
            self._rx.set_costas_mode(text)
        else:
            self._rx.costas_mode = text

    def _on_iqcorr_toggled(self, checked: bool):
        if self._guard or self._rx is None:
            return
        if hasattr(self._rx, "set_iq_correction_enabled"):
            self._rx.set_iq_correction_enabled(bool(checked))

    def _on_profile_changed(self, _):
        if self._guard or self._rx is None:
            return
        prof = self.profileCombo.currentData()
        if prof is None:
            prof = "generic"
        if hasattr(self._rx, "set_modulation_profile"):
            self._rx.set_modulation_profile(str(prof))
        # Remet des valeurs utiles pour TETRA par défaut.
        if str(prof) == "tetra":
            self._guard = True
            try:
                self.constMode.setCurrentIndex(max(0, self.constMode.findData("symbols")))
                self.constDomain.setCurrentIndex(max(0, self.constDomain.findData("differential")))
                self.symbolRateSpin.setValue(18.000)
                self.costasEnable.setChecked(True)
                self.costasMode.setCurrentText("qpsk")
                self.iqCorrEnable.setChecked(True)
            finally:
                self._guard = False
            # Appliquer explicitement côté RX après remise des contrôles.
            if hasattr(self._rx, "set_costas_enabled"):
                self._rx.set_costas_enabled(True)
            if hasattr(self._rx, "set_costas_mode"):
                self._rx.set_costas_mode("qpsk")
            if hasattr(self._rx, "set_iq_correction_enabled"):
                self._rx.set_iq_correction_enabled(True)
            self._rx.set_constellation_mode("symbols")
            if hasattr(self._rx, "set_constellation_domain"):
                self._rx.set_constellation_domain("differential")
            self._rx.set_symbol_rate(18_000.0)

    def _on_const_mode_changed(self, _):
        if self._guard or self._rx is None:
            return
        mode = self.constMode.currentData()
        if mode is None:
            mode = "raw"
        self._rx.set_constellation_mode(str(mode))

    def _on_symbol_rate_changed(self, ksym_s: float):
        if self._guard or self._rx is None:
            return
        self._rx.set_symbol_rate(float(ksym_s) * 1e3)

    def _on_const_domain_changed(self, _):
        if self._guard or self._rx is None:
            return
        domain = self.constDomain.currentData()
        if domain is None:
            domain = "iq"
        if hasattr(self._rx, "set_constellation_domain"):
            self._rx.set_constellation_domain(str(domain))

    @QtCore.pyqtSlot(dict)
    def _on_quality_updated(self, info: dict):
        state = str(info.get("state", "SEARCH"))
        evm = float(info.get("evm_pct", float("nan")))
        evm_rad = float(info.get("evm_rad_pct", float("nan")))
        evm_tan = float(info.get("evm_tan_pct", float("nan")))
        evm_rt = float(info.get("evm_rt_ratio", float("nan")))
        mer = float(info.get("mer_db", float("nan")))
        cmet = float(info.get("lock_metric", 0.0))
        sps = float(info.get("sps", 0.0))
        sps_nom = float(info.get("sps_nom", sps))
        sps_off_ppm = float(info.get("sps_off_ppm", 0.0))
        iq_imb = float(info.get("iq_imbalance", 0.0))
        cfo_hz = float(info.get("cfo_hz", 0.0))
        cfo_ppm = float(info.get("cfo_ppm", 0.0))
        ted_std = float(info.get("ted_std", 0.0))
        t_corr = float(info.get("timing_corr", 0.0))
        t_clips = int(info.get("timing_clips", 0))
        ecc = float(info.get("cluster_ecc", 0.0))
        eq_on = bool(info.get("eq_on", False))
        eq_err = float(info.get("eq_err", 0.0))
        eq_upd = float(info.get("eq_upd", 0.0))
        costas_act = bool(info.get("costas_active", False))
        hist = info.get("phase_hist", [0.0, 0.0, 0.0, 0.0])
        try:
            h_txt = "/".join(f"{int(round(100.0 * float(v))):02d}" for v in list(hist)[:4])
        except Exception:
            h_txt = "--/--/--/--"
        self.syncLabel.setText(
            f"Sync: {state} | EVM: {evm:.1f}% (Er:{evm_rad:.1f} Et:{evm_tan:.1f} R/T:{evm_rt:.2f}) | "
            f"MER: {mer:.1f} dB | C: {cmet:.2f} | sps: {sps:.3f} (nom:{sps_nom:.3f}, off:{sps_off_ppm:+.0f} ppm)\n"
            f"CFO: {cfo_hz:+.1f} Hz ({cfo_ppm:+.3f} ppm) | TEDσ: {ted_std:.3f} | Tcorr: {t_corr:+.4f} | "
            f"clips: {t_clips} | Ecc: {ecc:.2f} | H4: {h_txt} | IQ: {iq_imb:.3f} | "
            f"Costas:{'ON' if costas_act else 'OFF'} | EQ:{'ON' if eq_on else 'OFF'} "
            f"(err:{eq_err:.3f} upd:{eq_upd:.4f})"
        )
        if state == "LOCK":
            color = "#80ff80"
        elif state == "WEAK":
            color = "#ffe08a"
        else:
            color = "#ffd166"
        self.syncLabel.setStyleSheet(f"color: {color};")

    # — Audio FM —
    def _current_device_index(self):
        return self.audioDevice.currentData()

    def _on_fm_toggled(self, checked: bool):
        if self._rx is None or self._rx.demod is None:
            return
        if checked:
            dev = self._current_device_index()
            try:
                self._rx.demod.start(output_device=dev)
            except Exception as e:
                # si erreur device, on décoche
                self.fmEnable.blockSignals(True)
                self.fmEnable.setChecked(False)
                self.fmEnable.blockSignals(False)
                QtWidgets.QMessageBox.warning(self, "Audio error", str(e))
        else:
            self._rx.demod.stop()

    def _on_device_changed(self, _):
        if self._rx is None or self._rx.demod is None:
            return
        if self.fmEnable.isChecked():
            # redémarre sur le nouveau device
            dev = self._current_device_index()
            try:
                self._rx.demod.stop()
                self._rx.demod.start(output_device=dev)
            except Exception as e:
                QtWidgets.QMessageBox.warning(self, "Audio error", str(e))

    # — RX → UI —
    def _on_rx_freq_changed(self, f_hz: float):
        self._guard = True
        try:
            self.freqSpin.setValue(f_hz / 1e6)
        finally:
            self._guard = False

    def _on_rx_bw_changed(self, bw_hz: float):
        self._guard = True
        try:
            self.bwSpin.setValue(bw_hz / 1e3)
        finally:
            self._guard = False

    # — Spectrum → UI (sans réémettre) —
    def _on_spec_freq_changed(self, f_hz: float):
        self._guard = True
        try:
            self.freqSpin.blockSignals(True)
            self.freqSpin.setValue(f_hz / 1e6)
        finally:
            self.freqSpin.blockSignals(False)
            self._guard = False

    def _on_spec_bw_changed(self, bw_hz: float):
        self._guard = True
        try:
            self.bwSpin.blockSignals(True)
            self.bwSpin.setValue(bw_hz / 1e3)
        finally:
            self.bwSpin.blockSignals(False)
            self._guard = False


class ReceiverTabPage(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.rx_panel = ReceiverTab(self)
        lay = QtWidgets.QVBoxLayout(self)
        lay.setContentsMargins(6, 6, 6, 6)
        lay.addWidget(self.rx_panel)

    def bind(self, rx, spec_widget):
        self.rx_panel.bind(rx, spec_widget)
