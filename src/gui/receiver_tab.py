# src/gui/receiver_tab.py
from PyQt5 import QtWidgets, QtCore
from src.core.demodulators import FMDemodulator
import sounddevice as sd

class ReceiverTab(QtWidgets.QWidget):
    """
    Receiver panel with RF controls and audio demodulator selection.
    """
    request_set_frequency = QtCore.pyqtSignal(float)
    request_set_bandwidth = QtCore.pyqtSignal(float)
    request_set_costas_enabled = QtCore.pyqtSignal(bool)
    request_set_costas_mode = QtCore.pyqtSignal(str)
    request_set_iq_correction_enabled = QtCore.pyqtSignal(bool)
    request_set_modulation_profile = QtCore.pyqtSignal(str)
    request_set_constellation_mode = QtCore.pyqtSignal(str)
    request_set_constellation_domain = QtCore.pyqtSignal(str)
    request_set_symbol_rate = QtCore.pyqtSignal(float)
    request_set_demod_mode = QtCore.pyqtSignal(str)
    request_set_audio_enabled = QtCore.pyqtSignal(bool)
    request_set_audio_device = QtCore.pyqtSignal(int)

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

        # --- Audio demodulator ---
        sep = QtWidgets.QLabel("<b>Audio demodulator</b>")
        form.addRow(sep)

        self.audioEnable = QtWidgets.QCheckBox("Enable audio")
        self.demodButtonGroup = QtWidgets.QButtonGroup(self)
        self.demodButtons = {}
        demodLayout = QtWidgets.QHBoxLayout()
        for demod_key, label in (("am", "AM"), ("fm", "FM"), ("usb", "USB"), ("lsb", "LSB"), ("cw", "CW")):
            button = QtWidgets.QRadioButton(label)
            self.demodButtonGroup.addButton(button)
            self.demodButtons[demod_key] = button
            demodLayout.addWidget(button)
        demodLayout.addStretch(1)

        self.audioDevice = QtWidgets.QComboBox()
        self.refreshBtn = QtWidgets.QPushButton("↻")

        h = QtWidgets.QHBoxLayout()
        h.addWidget(self.audioDevice, 1)
        h.addWidget(self.refreshBtn, 0)
        form.addRow("Mode:", demodLayout)
        form.addRow("Output device:", h)
        form.addRow(self.audioEnable)

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
        self.audioEnable.toggled.connect(self._on_audio_toggled)
        self.audioDevice.currentIndexChanged.connect(self._on_device_changed)
        self.refreshBtn.clicked.connect(self._populate_devices)
        self.demodButtonGroup.buttonToggled.connect(self._on_demod_button_toggled)

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
        rx.demod_mode = getattr(rx, "demod_mode", "fm")

        self._populate_devices()
        self.request_set_frequency.connect(rx.set_selected_frequency, type=QtCore.Qt.QueuedConnection)
        self.request_set_bandwidth.connect(rx.set_bandwidth, type=QtCore.Qt.QueuedConnection)
        self.request_set_costas_enabled.connect(rx.set_costas_enabled, type=QtCore.Qt.QueuedConnection)
        self.request_set_costas_mode.connect(rx.set_costas_mode, type=QtCore.Qt.QueuedConnection)
        self.request_set_iq_correction_enabled.connect(rx.set_iq_correction_enabled, type=QtCore.Qt.QueuedConnection)
        self.request_set_modulation_profile.connect(rx.set_modulation_profile, type=QtCore.Qt.QueuedConnection)
        self.request_set_constellation_mode.connect(rx.set_constellation_mode, type=QtCore.Qt.QueuedConnection)
        self.request_set_constellation_domain.connect(rx.set_constellation_domain, type=QtCore.Qt.QueuedConnection)
        self.request_set_symbol_rate.connect(rx.set_symbol_rate, type=QtCore.Qt.QueuedConnection)
        self.request_set_demod_mode.connect(rx.set_demod_mode, type=QtCore.Qt.QueuedConnection)
        self.request_set_audio_enabled.connect(rx.set_audio_enabled, type=QtCore.Qt.QueuedConnection)
        self.request_set_audio_device.connect(rx.set_audio_output_device, type=QtCore.Qt.QueuedConnection)

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
            self._set_demod_button(rx.demod_mode)
            self.audioEnable.setChecked(bool(getattr(rx, "audio_enabled", False)))
        finally:
            self._guard = False

        rx.frequency_changed.connect(self._on_rx_freq_changed)
        rx.bandwidth_changed.connect(self._on_rx_bw_changed)
        rx.demodulator_changed.connect(self._on_rx_demod_changed)
        rx.audio_state_changed.connect(self._on_rx_audio_state_changed)
        rx.error.connect(self._on_rx_error)
        try:
            rx.quality_updated.connect(self._on_quality_updated)
        except Exception:
            pass

        spectrum_widget.receiver_frequency_changed.connect(self._on_spec_freq_changed)
        spectrum_widget.receiver_bandwidth_changed.connect(self._on_spec_bw_changed)
        self.request_set_audio_device.emit(self._current_device_index())

    # — UI → RX —
    def _on_ui_freq_changed(self, mhz: float):
        if self._guard or self._rx is None:
            return
        self.request_set_frequency.emit(mhz * 1e6)

    def _on_ui_bw_changed(self, khz: float):
        if self._guard or self._rx is None:
            return
        self.request_set_bandwidth.emit(khz * 1e3)

    def _set_demod_button(self, demod_mode: str):
        button = self.demodButtons.get(str(demod_mode).lower())
        if button is not None:
            button.setChecked(True)

    def _switch_demodulator(self, demod_mode: str):
        if self._rx is None:
            return
        self.request_set_demod_mode.emit(str(demod_mode).lower())

    def _on_demod_button_toggled(self, button, checked: bool):
        if not checked or self._guard or self._rx is None:
            return
        for demod_mode, candidate in self.demodButtons.items():
            if candidate is button:
                self._switch_demodulator(demod_mode)
                break

    def _on_costas_toggled(self, checked: bool):
        if self._rx is None: return
        self.request_set_costas_enabled.emit(bool(checked))

    def _on_costas_mode(self, text: str):
        if self._rx is None: return
        self.request_set_costas_mode.emit(text)

    def _on_iqcorr_toggled(self, checked: bool):
        if self._guard or self._rx is None:
            return
        self.request_set_iq_correction_enabled.emit(bool(checked))

    def _on_profile_changed(self, _):
        if self._guard or self._rx is None:
            return
        prof = self.profileCombo.currentData()
        if prof is None:
            prof = "generic"
        self.request_set_modulation_profile.emit(str(prof))
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
            self.request_set_costas_enabled.emit(True)
            self.request_set_costas_mode.emit("qpsk")
            self.request_set_iq_correction_enabled.emit(True)
            self.request_set_constellation_mode.emit("symbols")
            self.request_set_constellation_domain.emit("differential")
            self.request_set_symbol_rate.emit(18_000.0)

    def _on_const_mode_changed(self, _):
        if self._guard or self._rx is None:
            return
        mode = self.constMode.currentData()
        if mode is None:
            mode = "raw"
        self.request_set_constellation_mode.emit(str(mode))

    def _on_symbol_rate_changed(self, ksym_s: float):
        if self._guard or self._rx is None:
            return
        self.request_set_symbol_rate.emit(float(ksym_s) * 1e3)

    def _on_const_domain_changed(self, _):
        if self._guard or self._rx is None:
            return
        domain = self.constDomain.currentData()
        if domain is None:
            domain = "iq"
        self.request_set_constellation_domain.emit(str(domain))

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

    # — Audio —
    def _current_device_index(self):
        current = self.audioDevice.currentData()
        return -1 if current is None else int(current)

    def _on_audio_toggled(self, checked: bool):
        if self._rx is None:
            return
        self.request_set_audio_enabled.emit(bool(checked))

    def _on_device_changed(self, _):
        if self._rx is None:
            return
        self.request_set_audio_device.emit(self._current_device_index())

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

    @QtCore.pyqtSlot(str)
    def _on_rx_demod_changed(self, demod_mode: str):
        self._guard = True
        try:
            self._set_demod_button(demod_mode)
        finally:
            self._guard = False

    @QtCore.pyqtSlot(bool)
    def _on_rx_audio_state_changed(self, enabled: bool):
        self.audioEnable.blockSignals(True)
        try:
            self.audioEnable.setChecked(bool(enabled))
        finally:
            self.audioEnable.blockSignals(False)

    @QtCore.pyqtSlot(str)
    def _on_rx_error(self, message: str):
        QtWidgets.QMessageBox.warning(self, "Receiver error", message)

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
