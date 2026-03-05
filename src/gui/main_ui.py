# src/gui/main_ui.py
import time
from pathlib import Path
from PyQt5 import QtWidgets, QtCore, uic, QtGui

from src.gui.plots import SpectrumPlotWidget, WaterfallPlotWidget, ConstellationPlotWidget
from src.gui.receivers_ui import ReceiversUI

from src.core.sdr import SDRController
from src.core.receivers_manager import ReceiversManager
from src.core.receiver import Receiver

import pyqtgraph as pg


class SDRGUI(QtWidgets.QMainWindow):
    def __init__(self, thread_manager=None, parent=None):
        super().__init__(parent)
        # UI
        ui_path = Path(__file__).resolve().with_name("ui_main.ui")
        if not ui_path.exists():
            raise FileNotFoundError(f"UI introuvable: {ui_path}")
        uic.loadUi(str(ui_path), self)

        # --- Receivers manager + UI des onglets ---
        self.rx_mgr = ReceiversManager(self)
        self.receivers_ui = ReceiversUI(self)
        self.receivers_ui.addRequested.connect(lambda: self.add_new_receiver(make_current=True))
        self.receivers_ui.activated.connect(self._activate_rx)
        self.receivers_ui.closed.connect(self._on_rx_closed)

        self._active_rx = None  # RX actuellement contrôlé par le curseur

        # Debounce pour la fréquence centrale (molette/drag)
        self._freq_change_timer = QtCore.QTimer(self)
        self._freq_change_timer.setSingleShot(True)
        self._freq_change_timer.setInterval(150)
        self._pending_center_freq_mhz = None
        self._freq_change_timer.timeout.connect(self._apply_pending_center_freq)

        self.thread_manager = thread_manager
        self.controller = SDRController()
        self.controller.sample_rate_changed.connect(self._on_controller_fs_changed)
        time.sleep(0.5)  # SDRPlay warmup
        self.controller.center_frequency_changed.connect(self._set_spin_center_freq_from_controller)

        # 1) Fréquence centrale depuis l’UI
        init_freq_hz = float(self.freqSpinBox_2.value()) * 1e6
        self.controller.set_frequency(init_freq_hz)

        # 2) FS à 2.0 MHz
        self.controller.set_sample_rate(2_000_000)

        # --- Plots & DataStorage ---
        self.spectrumPlotWidget = SpectrumPlotWidget(
            self.mainPlotLayout, center_freq=self.controller.center_freq
        )
        self.controller.center_frequency_changed.connect(
            self.spectrumPlotWidget.update_center_frequency
        )
        # NOTE: NE PAS connecter update_selected_freq_line (single cursor legacy)
        # self.controller.center_frequency_changed.connect(
        #     self.spectrumPlotWidget.update_selected_freq_line
        # )

        self.waterfallPlotWidget = WaterfallPlotWidget(
            self.waterfallPlotLayout, self.histogramPlotLayout
        )
        self.constellationPlotWidget = ConstellationPlotWidget(
            self.constellationPlotLayout
        )

        ds = self.controller.data_storage
        ds.data_updated.connect(self.spectrumPlotWidget.update_plot)
        ds.data_updated.connect(self.spectrumPlotWidget.update_persistence)
        ds.data_recalculated.connect(self.spectrumPlotWidget.recalculate_plot)
        ds.data_recalculated.connect(self.spectrumPlotWidget.recalculate_persistence)
        ds.history_updated.connect(self.waterfallPlotWidget.update_plot)
        ds.history_recalculated.connect(self.waterfallPlotWidget.recalculate_plot)
        ds.average_updated.connect(self.spectrumPlotWidget.update_average)
        ds.baseline_updated.connect(self.spectrumPlotWidget.update_baseline)
        ds.peak_hold_max_updated.connect(self.spectrumPlotWidget.update_peak_hold_max)
        ds.peak_hold_min_updated.connect(self.spectrumPlotWidget.update_peak_hold_min)

        self.spectrumPlotWidget.plot.setXLink(self.waterfallPlotWidget.plot)

        # Etat initial (courbes)
        self.spectrumPlotWidget.main_curve = bool(self.mainCurveCheckBox.isChecked())
        self.spectrumPlotWidget.peak_hold_max = bool(self.peakHoldMaxCheckBox.isChecked())
        self.spectrumPlotWidget.peak_hold_min = bool(self.peakHoldMinCheckBox.isChecked())
        self.spectrumPlotWidget.average = bool(self.averageCheckBox.isChecked())
        self.spectrumPlotWidget.baseline = bool(self.baselineCheckBox.isChecked())
        self.spectrumPlotWidget.persistence = bool(self.persistenceCheckBox.isChecked())

        self.spectrumPlotWidget.clear_plot()
        self.spectrumPlotWidget.clear_peak_hold_max()
        self.spectrumPlotWidget.clear_peak_hold_min()
        self.spectrumPlotWidget.clear_average()
        self.spectrumPlotWidget.clear_baseline()

        # --- RX1 par défaut ---
        self._setup_default_receiver()

        # --- UI contrôles latéraux ---
        self._populate_combos_safely()
        self._connect_ui_signals()
        self.freqSpinBox_2.valueChanged.connect(self._on_center_freq_spin_changed)


    def _on_rx_closed(self, rx):
        # débranchement minimal
        try:
            if hasattr(rx, "_thread") and rx._thread is not None:
                rx._thread.quit()
                rx._thread.wait(500)
        except Exception:
            pass
        self.rx_mgr.remove(rx.name)
        rx.deleteLater()


    def _on_center_freq_spin_changed(self, mhz: float):
        self._pending_center_freq_mhz = float(mhz)
        self._freq_change_timer.start()

    def _apply_pending_center_freq(self):
        if self._pending_center_freq_mhz is None:
            return
        f_hz = self._pending_center_freq_mhz * 1e6
        self.controller.set_frequency(f_hz)
        self._pending_center_freq_mhz = None

    def _set_spin_center_freq_from_controller(self, f_hz: float):
        try:
            self.freqSpinBox_2.blockSignals(True)
            self.freqSpinBox_2.setValue(f_hz / 1e6)
        finally:
            self.freqSpinBox_2.blockSignals(False)

    # ---------- Init auxiliaire ----------
    def _populate_combos_safely(self):
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

    def _connect_ui_signals(self):
        self.startButton.clicked.connect(self.start_sdr)
        self.stopButton.clicked.connect(self.stop_sdr)
        self.sampleRateComboBox.currentIndexChanged.connect(self.update_sample_rate)
        self.antennaComboBox.currentIndexChanged.connect(self.set_antenna)
        self.IFGRHorizontalSlider.valueChanged.connect(self.update_ifgain)
        self.RFGRHorizontalSlider.valueChanged.connect(self.update_rfgain)
        self.AGCCheckBox.stateChanged.connect(self.set_agc)
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
                if self._active_rx is not None:
                    self.spectrumPlotWidget.set_receiver_selection(
                        self._active_rx.selected_freq, self._active_rx.bandwidth
                    )
                    self.spectrumPlotWidget.set_selection_color(self._active_rx.ui_color)
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

    def _next_rx_color(self):
        palette = [
            QtGui.QColor("red"),
            QtGui.QColor("cyan"),
            QtGui.QColor("magenta"),
            QtGui.QColor("yellow"),
            QtGui.QColor("green"),
            QtGui.QColor("white"),
        ]
        n = len(self.rx_mgr.all())
        return palette[(n - 1) % len(palette)]

    def _deactivate_rx(self, rx):
        if rx is None:
            return
        try:
            self.spectrumPlotWidget.receiver_frequency_changed.disconnect(rx.set_selected_frequency)
        except Exception:
            pass
        try:
            self.spectrumPlotWidget.receiver_bandwidth_changed.disconnect(rx.set_bandwidth)
        except Exception:
            pass
        try:
            if hasattr(self.controller, "iq_block"):
                self.controller.iq_block.disconnect(rx.process_block)
            else:
                self.controller.new_data.disconnect(rx.process_block)
        except Exception:
            pass
        try:
            rx.iq_out.disconnect(self.constellationPlotWidget.update_plot)
        except Exception:
            pass

    def _activate_rx(self, rx):
        if getattr(self, "_active_rx", None) not in (None, rx):
            self._deactivate_rx(self._active_rx)

        # Spectre -> RX (unique)
        try:
            self.spectrumPlotWidget.receiver_frequency_changed.disconnect(rx.set_selected_frequency)
        except Exception:
            pass
        try:
            self.spectrumPlotWidget.receiver_bandwidth_changed.disconnect(rx.set_bandwidth)
        except Exception:
            pass
        try:
            self.spectrumPlotWidget.receiver_frequency_changed.connect(
                rx.set_selected_frequency, type=QtCore.Qt.UniqueConnection
            )
        except TypeError:
            pass
        try:
            self.spectrumPlotWidget.receiver_bandwidth_changed.connect(
                rx.set_bandwidth, type=QtCore.Qt.UniqueConnection
            )
        except TypeError:
            pass

        # Flux IQ (unique)
        try:
            if hasattr(self.controller, "iq_block"):
                try: self.controller.iq_block.disconnect(rx.process_block)
                except Exception: pass
                self.controller.iq_block.connect(rx.process_block, type=QtCore.Qt.UniqueConnection)
            else:
                try: self.controller.new_data.disconnect(rx.process_block)
                except Exception: pass
                self.controller.new_data.connect(rx.process_block, type=QtCore.Qt.UniqueConnection)
        except TypeError:
            pass

        # Constellation: afficher l'IQ post-traitement du RX actif (incluant Costas si activé)
        try:
            try:
                rx.iq_out.disconnect(self.constellationPlotWidget.update_plot)
            except Exception:
                pass
            rx.iq_out.connect(
                self.constellationPlotWidget.update_plot,
                type=QtCore.Qt.UniqueConnection
            )
        except TypeError:
            pass

        # Overlays multi-RX
        self.spectrumPlotWidget.ensure_rx_overlay(
            rx.name, rx.ui_color, rx.selected_freq, rx.bandwidth, active=True
        )
        self.spectrumPlotWidget.set_active_rx(rx.name)
        self.spectrumPlotWidget.update_rx_overlay(rx.name, rx.selected_freq, rx.bandwidth)
        self.spectrumPlotWidget.set_selection_color(rx.ui_color)

        self._active_rx = rx
        try:
            self.iqcrtlCheckBox.blockSignals(True)
            self.iqcrtlCheckBox.setChecked(bool(getattr(rx, "iq_correction_enabled", True)))
        finally:
            self.iqcrtlCheckBox.blockSignals(False)

    def add_new_receiver(self, name: str = None, f_hz: float = None,
                         bw_hz: float = 25e3, enable_costas: bool = False,
                         make_current: bool = True):
        def _next_name():
            i = 1
            while self.rx_mgr.get(f"RX{i}") is not None:
                i += 1
            return f"RX{i}"

        if name is None or self.rx_mgr.get(name) is not None:
            name = _next_name()
        if f_hz is None:
            f_hz = self.controller.center_freq

        def get_center():
            return self.controller.center_freq

        rx = Receiver(
            name=name,
            sample_rate=self.controller.sample_rate,
            center_freq_provider=get_center,
            selected_freq=f_hz,
            bandwidth=bw_hz,
            enable_costas=enable_costas,
            costas_mode="qpsk",
            num_taps=511,
            parent=self,
        )
        try:
            rx.set_iq_correction_enabled(bool(self.iqcrtlCheckBox.isChecked()))
        except Exception:
            pass
        self.rx_mgr.add(rx)
        try:
            self.controller.sample_rate_about_to_change.connect(
                rx.on_sample_rate_about_to_change, type=QtCore.Qt.UniqueConnection
            )
        except TypeError:
            pass
        try:
            self.controller.sample_rate_changed.connect(
                rx.set_sample_rate, type=QtCore.Qt.UniqueConnection
            )
        except TypeError:
            pass

        rx.ui_color = self._next_rx_color()

        rx.frequency_changed.connect(
            lambda f, r=rx: self.spectrumPlotWidget.update_rx_overlay(r.name, f, r.bandwidth)
            if r is self._active_rx else None
        )
        rx.bandwidth_changed.connect(
            lambda bw, r=rx: self.spectrumPlotWidget.update_rx_overlay(r.name, r.selected_freq, bw)
            if r is self._active_rx else None
        )

        # Onglet (ReceiversUI)
        self.receivers_ui.add_tab_for_rx(rx, make_current=make_current)

        # Overlay visible même si pas actif
        self.spectrumPlotWidget.ensure_rx_overlay(
            rx.name, rx.ui_color, rx.selected_freq, rx.bandwidth, active=make_current
        )

        if make_current:
            self._activate_rx(rx)
        return rx

    def _on_controller_fs_about_to_change(self, new_fs: float):
        # Legacy hook conservé pour compatibilité.
        # Les RX sont déjà connectés directement à sample_rate_about_to_change.
        _ = new_fs

    def _on_controller_fs_changed(self, new_fs: float):
        # Optionnel : forcer un rafraîchissement du tracé ou de l’axe si besoin
        try:
            self.spectrumPlotWidget.recalculate_plot(self.controller.data_storage)
        except Exception:
            pass

    # ---------- Slots UI ----------
    def start_sdr(self):
        self.startButton.setEnabled(False)
        self.stopButton.setEnabled(True)
        self.controller.start()

    def stop_sdr(self):
        self.controller.stop()
        self.startButton.setEnabled(True)
        self.stopButton.setEnabled(False)

    def update_frequency(self):
        new_freq = float(self.freqSpinBox_2.value()) * 1e6
        self.controller.set_frequency(new_freq)

    def update_sample_rate(self):
        new_rate = self.sampleRateComboBox.currentData()
        if not new_rate:
            return
        self.controller.set_sample_rate(new_rate)

    def set_antenna(self):
        antenna = self.antennaComboBox.currentText()
        self.controller.set_antenna(antenna)
        self.biasTeeCheckBox.setEnabled(antenna == "Antenna B")

    def update_ifgain(self):
        self.controller.update_if_gain(self.IFGRHorizontalSlider.value())

    def update_rfgain(self):
        self.controller.update_rf_gain(self.RFGRHorizontalSlider.value())

    def set_agc(self):
        agc = self.AGCCheckBox.isChecked()
        self.controller.update_agc(agc)
        self.IFGRHorizontalSlider.setEnabled(not agc)
        if not agc:
            self.update_ifgain()

    def set_iqctrl(self):
        enabled = bool(self.iqcrtlCheckBox.isChecked())
        rx = getattr(self, "_active_rx", None)
        if rx is None:
            return
        try:
            rx.set_iq_correction_enabled(enabled)
        except Exception:
            pass
    def set_biastee(self): pass
    def set_fmnotch(self): pass
    def set_dabnotch(self): pass

    def shutdown(self):
        try:
            self.stop_sdr()
        except Exception:
            pass

    @QtCore.pyqtSlot(bool)
    def on_mainCurveCheckBox_toggled(self, checked: bool):
        self.spectrumPlotWidget.main_curve = checked
        if getattr(self.spectrumPlotWidget.curve, "xData", None) is None:
            self.spectrumPlotWidget.update_plot(self.controller.data_storage)
        self.spectrumPlotWidget.curve.setVisible(checked)

    @QtCore.pyqtSlot(bool)
    def on_maxHold_toggled(self, checked: bool):
        self.spectrumPlotWidget.peak_hold_max = bool(checked)
        # force un rafraîchissement de la courbe peak-hold
        self.spectrumPlotWidget.update_peak_hold_max(self.controller.data_storage, force=True)

    @QtCore.pyqtSlot(bool)
    def on_minHold_toggled(self, checked: bool):
        self.spectrumPlotWidget.peak_hold_min = bool(checked)
        self.spectrumPlotWidget.update_peak_hold_min(self.controller.data_storage, force=True)

    @QtCore.pyqtSlot(bool)
    def on_average_toggled(self, checked: bool):
        self.spectrumPlotWidget.average = bool(checked)
        self.spectrumPlotWidget.update_average(self.controller.data_storage, force=True)

    @QtCore.pyqtSlot(bool)
    def on_smoothing_toggled(self, checked: bool):
        try:
            self.controller.data_storage.set_smooth(bool(checked))
        except Exception:
            pass
        self.spectrumPlotWidget.update_plot(self.controller.data_storage, force=True)

    @QtCore.pyqtSlot(bool)
    def on_persistence_toggled(self, checked: bool):
        self.spectrumPlotWidget.persistence = bool(checked)
        if checked:
            self.spectrumPlotWidget.recalculate_persistence(self.controller.data_storage)
        else:
            self.spectrumPlotWidget.clear_persistence()

    @QtCore.pyqtSlot(bool)
    def on_baseline_toggled(self, checked: bool):
        self.spectrumPlotWidget.baseline = bool(checked)
        self.spectrumPlotWidget.update_baseline(self.controller.data_storage, force=True)

    @QtCore.pyqtSlot(bool)
    def on_subtract_baseline_toggled(self, checked: bool):
        ds = self.controller.data_storage
        # auto-snapshot si aucune baseline
        if checked and (getattr(ds, "baseline", None) is None or getattr(ds, "baseline_x", None) is None):
            self.spectrumPlotWidget.snapshot_baseline_from(ds, window_pts=151)
            # si l’UI a la case “Baseline”, coche-la au besoin pour visualiser la magenta
            if hasattr(self, "baselineCheckBox"):
                self.baselineCheckBox.setChecked(True)

        self.spectrumPlotWidget.subtract_baseline = bool(checked)
        # redraw immédiat
        self.spectrumPlotWidget.update_plot(ds, force=True)

    def on_baseline_snapshot(self):
        """Bouton '…' baseline: capture la baseline courante."""
        self.spectrumPlotWidget.snapshot_baseline_from(self.controller.data_storage)
        # Si la case "Baseline" est cochée, on s'assure que ça s'affiche :
        try:
            if getattr(self, "baselineCheckBox", None) and self.baselineCheckBox.isChecked():
                self.spectrumPlotWidget.update_baseline(self.controller.data_storage, force=True)
        except Exception:
            pass

    def on_colors_clicked(self):
        col = QtGui.QColorDialog.getColor(QtGui.QColor("yellow"), self, "Main curve color")
        if col.isValid():
            # mettre à jour juste la couleur principale; à toi d'étendre aux autres via un mini-dialog si besoin
            self.spectrumPlotWidget.main_color = pg.mkColor(col)
            self.spectrumPlotWidget.set_colors()
            self.spectrumPlotWidget.update_plot(self.controller.data_storage, force=True)
