# src/gui/main_ui.py
from pathlib import Path
from PyQt5 import QtWidgets, QtCore, uic, QtGui

from src.config.settings import UI_FILE_NAME
from src.gui.display_controller import DisplayController
from src.gui.gain_table_ui import AutoGainTableDock
from src.gui.receivers_ui import ReceiversUI
from src.gui.monitoring_controller import MonitoringDockController
from src.gui.receiver_runtime import ReceiverRuntimeCoordinator

from src.core.sdr import SDRController
from src.core.receivers_manager import ReceiversManager
from src.tools.gain_table import clamp_lna_state, lna_attenuation_db, max_lna_state_for_frequency


SPECTRUM_TRACE_SMOOTHING_PRESETS = [
    ("Off", 1.0),
    ("Light", 0.65),
    ("Medium", 0.35),
    ("Strong", 0.18),
]


class SDRGUI(QtWidgets.QMainWindow):
    """Main application window that wires together the SDR controller and GUI helpers."""

    def __init__(self, thread_manager=None, parent=None):
        super().__init__(parent)
        # UI
        ui_path = Path(__file__).resolve().with_name(UI_FILE_NAME)
        if not ui_path.exists():
            raise FileNotFoundError(f"UI file not found: {ui_path}")
        uic.loadUi(str(ui_path), self)

        # --- Receivers manager + UI des onglets ---
        self.rx_mgr = ReceiversManager(self)
        self.receivers_ui = ReceiversUI(self)
        self.receivers_ui.addRequested.connect(lambda: self.add_new_receiver(make_current=True))
        self.receivers_ui.activated.connect(self._activate_rx)
        self.receivers_ui.closed.connect(self._on_rx_closed)

        # Debounce pour la fréquence centrale (molette/drag)
        self._freq_change_timer = QtCore.QTimer(self)
        self._freq_change_timer.setSingleShot(True)
        self._freq_change_timer.setInterval(150)
        self._pending_center_freq_mhz = None
        self._freq_change_timer.timeout.connect(self._apply_pending_center_freq)

        self.thread_manager = thread_manager
        self.controller = SDRController(thread_manager=thread_manager)
        self.controller.sample_rate_changed.connect(self._on_controller_fs_changed)
        self.controller.center_frequency_changed.connect(self._set_spin_center_freq_from_controller)
        self.controller.center_frequency_changed.connect(self._on_controller_center_frequency_changed)
        self._current_center_frequency_hz = float(self.controller.center_freq)
        self.auto_gain_dock = None

        # 1) Fréquence centrale depuis l’UI
        init_freq_hz = float(self.freqSpinBox_2.value()) * 1e6
        self.controller.set_frequency(init_freq_hz)

        # 2) FS à 2.0 MHz
        self.controller.set_sample_rate(2_000_000)

        self.display_controller = DisplayController(self, self.controller)
        self.display_controller.setup()
        self.spectrumPlotWidget = self.display_controller.spectrum_plot
        self.waterfallPlotWidget = self.display_controller.waterfall_plot
        self.constellationPlotWidget = self.display_controller.constellation_plot
        self.receiver_runtime = ReceiverRuntimeCoordinator(
            main_window=self,
            controller=self.controller,
            receivers_ui=self.receivers_ui,
            rx_mgr=self.rx_mgr,
            spectrum_widget=self.spectrumPlotWidget,
            constellation_widget=self.constellationPlotWidget,
            iqctrl_checkbox=self.iqcrtlCheckBox,
            thread_manager=self.thread_manager,
        )
        self.monitoring_controller = MonitoringDockController(
            self,
            thread_manager=self.thread_manager,
            sdr_controller=self.controller,
            receiver_runtime=self.receiver_runtime,
        )
        self.monitoring_controller.setup()
        self._setup_gain_controls_ui()
        self._setup_auto_gain_dock()

        # --- RX1 par défaut ---
        self._setup_default_receiver()

        # --- UI contrôles latéraux ---
        self._populate_combos_safely()
        self._connect_ui_signals()
        self.freqSpinBox_2.valueChanged.connect(self._on_center_freq_spin_changed)

    def _on_rx_closed(self, rx):
        """Forward a closed receiver tab to the runtime coordinator."""
        self.receiver_runtime.close_rx(rx)

    def _on_center_freq_spin_changed(self, mhz: float):
        """Debounce center-frequency edits triggered by the spin box."""
        self._pending_center_freq_mhz = float(mhz)
        self._freq_change_timer.start()

    def _apply_pending_center_freq(self):
        """Apply the debounced center-frequency value to the SDR controller."""
        if self._pending_center_freq_mhz is None:
            return
        f_hz = self._pending_center_freq_mhz * 1e6
        self.controller.set_frequency(f_hz)
        self._pending_center_freq_mhz = None

    def _set_spin_center_freq_from_controller(self, f_hz: float):
        """Reflect controller-side frequency updates back into the spin box."""
        try:
            self.freqSpinBox_2.blockSignals(True)
            self.freqSpinBox_2.setValue(f_hz / 1e6)
        finally:
            self.freqSpinBox_2.blockSignals(False)

    def _on_controller_center_frequency_changed(self, f_hz: float) -> None:
        """Refresh frequency-dependent gain helpers after controller updates."""
        self._current_center_frequency_hz = float(f_hz)
        if not hasattr(self, "RFGRHorizontalSlider"):
            return
        self._update_rf_slider_range()
        if self.auto_gain_dock is not None:
            self.auto_gain_dock.widget.set_current_frequency(f_hz)
        if hasattr(self, "autoGainCheckBox") and self.autoGainCheckBox.isChecked():
            self._apply_auto_gain_profile()
        else:
            self._update_gain_labels()

    # ---------- Init auxiliaire ----------
    def _populate_combos_safely(self):
        """Populate hardware-dependent combo boxes without triggering change handlers."""
        self.sampleRateComboBox.blockSignals(True)
        self.antennaComboBox.blockSignals(True)
        try:
            self.sampleRateComboBox.clear()
            for rate in self.controller.hwinfo.get("sampleRates", []):
                self.sampleRateComboBox.addItem(f"{rate / 1e6:.1f} MHz", rate)

            target = 2_000_000
            best_idx, best_err = None, None
            for i in range(self.sampleRateComboBox.count()):
                val = self.sampleRateComboBox.itemData(i)
                if val is None: continue
                err = abs(int(val) - target)
                if best_err is None or err < best_err:
                    best_err, best_idx = err, i
            if best_idx is not None:
                self.sampleRateComboBox.setCurrentIndex(best_idx)

            self.antennaComboBox.clear()
            for ant in self.controller.hwinfo.get("antennas", []):
                self.antennaComboBox.addItem(ant)
        finally:
            self.sampleRateComboBox.blockSignals(False)
            self.antennaComboBox.blockSignals(False)

    def _setup_gain_controls_ui(self) -> None:
        """Install gain-related helper widgets in the source controls dock."""
        layout = self.controlsDockWidgetContents.layout()

        self.ifAttenuationValueLabel = QtWidgets.QLabel(self.controlsDockWidgetContents)
        self.ifAttenuationValueLabel.setObjectName("ifAttenuationValueLabel")
        self.ifAttenuationValueLabel.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        layout.addWidget(self.ifAttenuationValueLabel, 5, 1)

        self.lnaAttenuationValueLabel = QtWidgets.QLabel(self.controlsDockWidgetContents)
        self.lnaAttenuationValueLabel.setObjectName("lnaAttenuationValueLabel")
        self.lnaAttenuationValueLabel.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        layout.addWidget(self.lnaAttenuationValueLabel, 6, 1)

        self.autoGainCheckBox = QtWidgets.QCheckBox("Auto table", self.controlsDockWidgetContents)
        self.autoGainCheckBox.setObjectName("autoGainCheckBox")
        self.autoGainCheckBox.setToolTip("Use the auto gain lookup table instead of manual sliders.")
        layout.addWidget(self.autoGainCheckBox, 7, 1)

        self.traceAverageLabel = QtWidgets.QLabel("Trace avg:", self.controlsDockWidgetContents)
        self.traceAverageLabel.setObjectName("traceAverageLabel")
        self.traceAverageComboBox = QtWidgets.QComboBox(self.controlsDockWidgetContents)
        self.traceAverageComboBox.setObjectName("traceAverageComboBox")
        self.traceAverageComboBox.setToolTip("Temporal FFT smoothing. Higher levels stabilize the trace with minimal FPS cost.")
        for label, alpha in SPECTRUM_TRACE_SMOOTHING_PRESETS:
            self.traceAverageComboBox.addItem(label, float(alpha))
        layout.addWidget(self.traceAverageLabel, 5, 2)
        layout.addWidget(self.traceAverageComboBox, 6, 2)
        self._set_trace_average_preset(self.controller.spectrum_trace_alpha)

        self._set_slider_value(self.IFGRHorizontalSlider, int(self.controller.if_gain))
        self._set_slider_value(self.RFGRHorizontalSlider, int(self.controller.rf_gain))
        self._update_rf_slider_range()
        self._update_gain_labels()

        if hasattr(self, "smoothButton"):
            self.smoothButton.hide()

    def _setup_auto_gain_dock(self) -> None:
        """Create the editable auto-gain dock and expose it in the View menu."""
        self.auto_gain_dock = AutoGainTableDock(self)
        self.addDockWidget(QtCore.Qt.RightDockWidgetArea, self.auto_gain_dock)
        if hasattr(self, "settingsDockWidget"):
            self.tabifyDockWidget(self.settingsDockWidget, self.auto_gain_dock)
        self.auto_gain_dock.widget.activeLevelChanged.connect(self._on_auto_gain_profile_changed)
        self.auto_gain_dock.widget.profilesChanged.connect(self._on_auto_gain_profiles_changed)
        self.auto_gain_dock.widget.set_current_frequency(self._current_center_frequency_hz)

        menu_view = getattr(self.monitoring_controller, "menu_view", None)
        if menu_view is not None:
            action = QtWidgets.QAction("Auto Gain Table", self)
            action.triggered.connect(self.show_auto_gain_dock)
            menu_view.addAction(action)

    def _connect_ui_signals(self):
        """Bind Qt widgets to their corresponding controller and helper slots."""
        self.startButton.clicked.connect(self.start_sdr)
        self.stopButton.clicked.connect(self.stop_sdr)
        self.sampleRateComboBox.currentIndexChanged.connect(self.update_sample_rate)
        self.antennaComboBox.currentIndexChanged.connect(self.set_antenna)
        self.IFGRHorizontalSlider.valueChanged.connect(self.update_ifgain)
        self.RFGRHorizontalSlider.valueChanged.connect(self.update_rfgain)
        self.AGCCheckBox.stateChanged.connect(self.set_agc)
        self.autoGainCheckBox.toggled.connect(self.set_auto_gain_mode)
        self.biasTeeCheckBox.stateChanged.connect(self.set_biastee)
        self.FMNotchCheckBox.stateChanged.connect(self.set_fmnotch)
        self.DABNotchCheckBox.stateChanged.connect(self.set_dabnotch)
        self.iqcrtlCheckBox.stateChanged.connect(self.set_iqctrl)

        if hasattr(self, "peakHoldMaxCheckBox"):
            self.peakHoldMaxCheckBox.toggled.connect(self.on_maxHold_toggled)
        if hasattr(self, "peakHoldMinCheckBox"):
            self.peakHoldMinCheckBox.toggled.connect(self.on_minHold_toggled)
        if hasattr(self, "averageCheckBox"):
            self.averageCheckBox.toggled.connect(self.on_average_toggled)
        if hasattr(self, "smoothCheckBox"):
            self.smoothCheckBox.toggled.connect(self.on_smoothing_toggled)
        if hasattr(self, "traceAverageComboBox"):
            self.traceAverageComboBox.currentIndexChanged.connect(self.on_trace_average_changed)
        if hasattr(self, "persistenceCheckBox"):
            self.persistenceCheckBox.toggled.connect(self.on_persistence_toggled)
        if hasattr(self, "baselineCheckBox"):
            self.baselineCheckBox.toggled.connect(self.on_baseline_toggled)
        if hasattr(self, "subtractBaselineCheckBox"):
            self.subtractBaselineCheckBox.toggled.connect(self.on_subtract_baseline_toggled)
        if hasattr(self, "colorsButton"):
            self.colorsButton.clicked.connect(self.on_colors_clicked)
        if hasattr(self, "baselineButton"):
            self.baselineButton.clicked.connect(self.on_baseline_snapshot)

    # ---------- Receivers ----------
    def _setup_default_receiver(self):
        """Create the first receiver and ensure its overlay appears on first data."""
        rx1 = self.add_new_receiver(
            name="RX1",
            f_hz=self.controller.center_freq,
            bw_hz=25e3,
            enable_costas=False,
            make_current=True,
        )
        self._activate_rx(rx1)
        self.rx1 = rx1

        # Afficher correctement l’overlay à la 1ère data
        def _ensure_overlay_visible_once(*_):
            try:
                active_rx = self.receiver_runtime.active_rx
                if active_rx is not None:
                    self.spectrumPlotWidget.set_receiver_selection(
                        active_rx.selected_freq, active_rx.bandwidth
                    )
                    self.spectrumPlotWidget.set_selection_color(active_rx.ui_color)
            finally:
                # se débrancher après la première exécution
                try:
                    self.controller.data_storage.data_updated.disconnect(_ensure_overlay_visible_once)
                except Exception:
                    pass

        try:
            # Connexion “une fois” (pas besoin d’invokeMethod)
            self.controller.data_storage.data_updated.connect(
                _ensure_overlay_visible_once, type=QtCore.Qt.UniqueConnection
            )
        except TypeError:
            pass

    def _deactivate_rx(self, rx):
        """Detach a receiver from the active UI plumbing."""
        self.receiver_runtime.deactivate_rx(rx)

    def _activate_rx(self, rx):
        """Make a receiver the current target for UI interactions."""
        self.receiver_runtime.activate_rx(rx)

    def add_new_receiver(self, name: str = None, f_hz: float = None,
                         bw_hz: float = 25e3, enable_costas: bool = False,
                         make_current: bool = True):
        """Create a new receiver through the runtime coordinator."""
        return self.receiver_runtime.add_new_receiver(
            name=name,
            f_hz=f_hz,
            bw_hz=bw_hz,
            enable_costas=enable_costas,
            make_current=make_current,
        )

    def _on_controller_fs_about_to_change(self, new_fs: float):
        """Legacy compatibility hook kept for older signal wiring."""
        # Legacy hook conservé pour compatibilité.
        # Les RX sont déjà connectés directement à sample_rate_about_to_change.
        _ = new_fs

    def _on_controller_fs_changed(self, new_fs: float):
        """Notify plot helpers that the controller sample rate has changed."""
        _ = new_fs
        if not hasattr(self, "display_controller"):
            return
        self.display_controller.on_controller_sample_rate_changed()

    # ---------- Slots UI ----------
    def start_sdr(self):
        """Start SDR acquisition and update the main transport buttons."""
        self.startButton.setEnabled(False)
        self.stopButton.setEnabled(True)
        self.controller.start()

    def stop_sdr(self):
        """Stop SDR acquisition and restore the main transport buttons."""
        self.controller.stop()
        self.startButton.setEnabled(True)
        self.stopButton.setEnabled(False)

    def update_frequency(self):
        """Push the current center-frequency widget value into the controller."""
        new_freq = float(self.freqSpinBox_2.value()) * 1e6
        self.controller.set_frequency(new_freq)

    def update_sample_rate(self):
        """Apply the selected sample rate on the next event-loop turn."""
        new_rate = self.sampleRateComboBox.currentData()
        if not new_rate:
            return
        QtCore.QTimer.singleShot(
            0,
            lambda rate=float(new_rate): self.controller.set_sample_rate(rate),
        )

    def set_antenna(self):
        """Select the active antenna and toggle related UI controls."""
        antenna = self.antennaComboBox.currentText()
        self.controller.set_antenna(antenna)
        self.biasTeeCheckBox.setEnabled(antenna == "Antenna B")

    def update_ifgain(self):
        """Forward the IF gain slider value to the SDR controller."""
        if self.autoGainCheckBox.isChecked():
            return
        self.controller.update_if_gain(self.IFGRHorizontalSlider.value())
        self._update_gain_labels()

    def update_rfgain(self):
        """Forward the RF gain slider value to the SDR controller."""
        if self.autoGainCheckBox.isChecked():
            return
        value = clamp_lna_state(self._current_center_frequency_hz, self.RFGRHorizontalSlider.value())
        if value != self.RFGRHorizontalSlider.value():
            self._set_slider_value(self.RFGRHorizontalSlider, value)
        self.controller.update_rf_gain(value)
        self._update_gain_labels()

    def set_agc(self):
        """Toggle AGC and keep the IF gain slider in a coherent state."""
        if self.autoGainCheckBox.isChecked():
            try:
                self.AGCCheckBox.blockSignals(True)
                self.AGCCheckBox.setChecked(False)
            finally:
                self.AGCCheckBox.blockSignals(False)
            self.controller.update_agc(False)
            self.IFGRHorizontalSlider.setEnabled(False)
            return
        agc = self.AGCCheckBox.isChecked()
        self.controller.update_agc(agc)
        self.IFGRHorizontalSlider.setEnabled(not agc)
        if not agc:
            self.update_ifgain()

    def set_iqctrl(self):
        """Enable or disable IQ correction on the active receiver worker."""
        enabled = bool(self.iqcrtlCheckBox.isChecked())
        rx = self.receiver_runtime.active_rx
        if rx is None:
            return
        try:
            QtCore.QMetaObject.invokeMethod(
                rx,
                "set_iq_correction_enabled",
                QtCore.Qt.QueuedConnection,
                QtCore.Q_ARG(bool, enabled),
            )
        except Exception:
            pass
    def set_biastee(self): pass
    def set_fmnotch(self): pass
    def set_dabnotch(self): pass

    def set_auto_gain_mode(self, enabled: bool) -> None:
        """Switch between the editable auto-gain table and manual gain sliders."""
        enabled = bool(enabled)
        if enabled:
            try:
                self.AGCCheckBox.blockSignals(True)
                self.AGCCheckBox.setChecked(False)
            finally:
                self.AGCCheckBox.blockSignals(False)
            self.controller.update_agc(False)
            self.AGCCheckBox.setEnabled(False)
            self.IFGRHorizontalSlider.setEnabled(False)
            self.RFGRHorizontalSlider.setEnabled(False)
            self._apply_auto_gain_profile()
        else:
            self.AGCCheckBox.setEnabled(True)
            self.RFGRHorizontalSlider.setEnabled(True)
            self.IFGRHorizontalSlider.setEnabled(not self.AGCCheckBox.isChecked())
            self._update_gain_labels()

    def _on_auto_gain_profile_changed(self, _level_dbm: int) -> None:
        """Apply the newly selected auto-gain row when auto mode is active."""
        if self.autoGainCheckBox.isChecked():
            self._apply_auto_gain_profile()

    def _on_auto_gain_profiles_changed(self, _profiles: object) -> None:
        """Re-apply the current auto pair after a table edit."""
        if self.autoGainCheckBox.isChecked():
            self._apply_auto_gain_profile()

    def _apply_auto_gain_profile(self) -> None:
        """Apply the auto-gain pair matching the current frequency band."""
        if self.auto_gain_dock is None:
            return
        lna_state, if_gain = self.auto_gain_dock.widget.get_active_pair_for_frequency(
            self._current_center_frequency_hz
        )
        self._apply_gain_pair(lna_state=lna_state, if_gain=if_gain)

    def _apply_gain_pair(self, lna_state: int, if_gain: int) -> None:
        """Apply a complete gain pair and mirror it into the UI."""
        rf_value = clamp_lna_state(self._current_center_frequency_hz, lna_state)
        if_value = int(max(self.IFGRHorizontalSlider.minimum(), min(int(if_gain), self.IFGRHorizontalSlider.maximum())))
        self.controller.update_rf_gain(rf_value)
        self.controller.update_if_gain(if_value)
        self._set_slider_value(self.RFGRHorizontalSlider, rf_value)
        self._set_slider_value(self.IFGRHorizontalSlider, if_value)
        self._update_gain_labels()

    def _update_rf_slider_range(self) -> None:
        """Clamp the RF/LNA slider to the valid state range for the current band."""
        max_state = int(max_lna_state_for_frequency(self._current_center_frequency_hz))
        self.RFGRHorizontalSlider.setMinimum(0)
        self.RFGRHorizontalSlider.setMaximum(max_state)
        clamped_value = clamp_lna_state(self._current_center_frequency_hz, self.controller.rf_gain)
        if int(self.controller.rf_gain) != clamped_value:
            self.controller.update_rf_gain(clamped_value)
        self._set_slider_value(self.RFGRHorizontalSlider, clamped_value)

    def _update_gain_labels(self) -> None:
        """Refresh the visible LNA and IF attenuation labels."""
        lna_state = clamp_lna_state(self._current_center_frequency_hz, self.controller.rf_gain)
        lna_attn_db = lna_attenuation_db(self._current_center_frequency_hz, lna_state)
        if_attn_db = int(self.controller.if_gain)
        self.lnaAttenuationValueLabel.setText(f"LNA attn: {lna_attn_db} dB (state {lna_state})")
        self.ifAttenuationValueLabel.setText(f"IF attn: {if_attn_db} dB")

    @staticmethod
    def _set_slider_value(slider: QtWidgets.QSlider, value: int) -> None:
        """Update a slider without triggering its change handlers."""
        try:
            slider.blockSignals(True)
            slider.setValue(int(value))
        finally:
            slider.blockSignals(False)

    def show_auto_gain_dock(self) -> None:
        """Present the auto-gain dock as a floating tool window."""
        if self.auto_gain_dock is None:
            return
        self.auto_gain_dock.setFloating(True)
        self.auto_gain_dock.resize(QtCore.QSize(900, 420))
        self.auto_gain_dock.show()
        self.auto_gain_dock.raise_()
        self.auto_gain_dock.activateWindow()

    def shutdown(self):
        """Stop acquisition, close receiver workers, and stop tracked background threads."""
        try:
            self.stop_sdr()
        except Exception:
            pass
        self.receiver_runtime.shutdown()
        if self.thread_manager is not None:
            try:
                self.thread_manager.stop_all_threads()
            except Exception:
                pass

    @QtCore.pyqtSlot(bool)
    def on_mainCurveCheckBox_toggled(self, checked: bool):
        self.display_controller.on_main_curve_toggled(checked)

    @QtCore.pyqtSlot(bool)
    def on_maxHold_toggled(self, checked: bool):
        self.display_controller.on_max_hold_toggled(checked)

    @QtCore.pyqtSlot(bool)
    def on_minHold_toggled(self, checked: bool):
        self.display_controller.on_min_hold_toggled(checked)

    @QtCore.pyqtSlot(bool)
    def on_average_toggled(self, checked: bool):
        self.display_controller.on_average_toggled(checked)

    @QtCore.pyqtSlot(bool)
    def on_smoothing_toggled(self, checked: bool):
        self.display_controller.on_smoothing_toggled(checked)

    @QtCore.pyqtSlot(int)
    def on_trace_average_changed(self, _index: int):
        if not hasattr(self, "traceAverageComboBox"):
            return
        alpha = self.traceAverageComboBox.currentData()
        if alpha is None:
            return
        self.controller.set_spectrum_trace_alpha(float(alpha))

    def _set_trace_average_preset(self, alpha: float) -> None:
        if not hasattr(self, "traceAverageComboBox"):
            return
        target = float(alpha)
        best_index = 0
        best_error = None
        self.traceAverageComboBox.blockSignals(True)
        try:
            for index in range(self.traceAverageComboBox.count()):
                value = self.traceAverageComboBox.itemData(index)
                if value is None:
                    continue
                error = abs(float(value) - target)
                if best_error is None or error < best_error:
                    best_error = error
                    best_index = index
            self.traceAverageComboBox.setCurrentIndex(best_index)
        finally:
            self.traceAverageComboBox.blockSignals(False)

    @QtCore.pyqtSlot(bool)
    def on_persistence_toggled(self, checked: bool):
        self.display_controller.on_persistence_toggled(checked)

    @QtCore.pyqtSlot(bool)
    def on_baseline_toggled(self, checked: bool):
        self.display_controller.on_baseline_toggled(checked)

    @QtCore.pyqtSlot(bool)
    def on_subtract_baseline_toggled(self, checked: bool):
        self.display_controller.on_subtract_baseline_toggled(checked)

    def on_baseline_snapshot(self):
        self.display_controller.on_baseline_snapshot()

    def on_colors_clicked(self):
        self.display_controller.on_colors_clicked()
