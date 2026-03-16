"""Display and side-panel helpers for the main SDR window."""

from __future__ import annotations

from PyQt5 import QtCore, QtGui
import pyqtgraph as pg

from src.gui.plots import ConstellationPlotWidget, SpectrumPlotWidget, WaterfallPlotWidget


class DisplayController:
    """Own plot widgets, data bindings, and spectrum display actions."""

    def __init__(self, main_window, controller) -> None:
        self.main_window = main_window
        self.controller = controller
        self.spectrum_plot = SpectrumPlotWidget(
            main_window.mainPlotLayout,
            center_freq=controller.center_freq,
        )
        self.waterfall_plot = WaterfallPlotWidget(
            main_window.waterfallPlotLayout,
            main_window.histogramPlotLayout,
        )
        self.constellation_plot = ConstellationPlotWidget(
            main_window.constellationPlotLayout
        )

    def setup(self) -> None:
        self._bind_controller()
        self._apply_initial_state()

    def _bind_controller(self) -> None:
        self.controller.center_frequency_changed.connect(
            self.spectrum_plot.update_center_frequency
        )
        self.spectrum_plot.visible_span_changed.connect(
            self.controller.update_fft_for_view
        )

        ds = self.controller.data_storage
        ds.data_updated.connect(self.spectrum_plot.update_plot)
        ds.data_updated.connect(self.spectrum_plot.update_persistence)
        ds.data_recalculated.connect(self.spectrum_plot.recalculate_plot)
        ds.data_recalculated.connect(self.spectrum_plot.recalculate_persistence)
        ds.history_updated.connect(self.waterfall_plot.update_plot)
        ds.history_recalculated.connect(self.waterfall_plot.recalculate_plot)
        ds.average_updated.connect(self.spectrum_plot.update_average)
        ds.baseline_updated.connect(self.spectrum_plot.update_baseline)
        ds.peak_hold_max_updated.connect(self.spectrum_plot.update_peak_hold_max)
        ds.peak_hold_min_updated.connect(self.spectrum_plot.update_peak_hold_min)

        self.spectrum_plot.plot.setXLink(self.waterfall_plot.plot)

    def _apply_initial_state(self) -> None:
        w = self.main_window
        ds = self.controller.data_storage
        self.spectrum_plot.main_curve = bool(w.mainCurveCheckBox.isChecked())
        self.spectrum_plot.peak_hold_max = bool(w.peakHoldMaxCheckBox.isChecked())
        self.spectrum_plot.peak_hold_min = bool(w.peakHoldMinCheckBox.isChecked())
        self.spectrum_plot.average = bool(w.averageCheckBox.isChecked())
        self.spectrum_plot.baseline = bool(w.baselineCheckBox.isChecked())
        self.spectrum_plot.persistence = bool(w.persistenceCheckBox.isChecked())

        ds.set_compute_average_enabled(self.spectrum_plot.average)
        ds.set_compute_peak_max_enabled(self.spectrum_plot.peak_hold_max)
        ds.set_compute_peak_min_enabled(self.spectrum_plot.peak_hold_min)

        self.spectrum_plot.clear_plot()
        self.spectrum_plot.clear_peak_hold_max()
        self.spectrum_plot.clear_peak_hold_min()
        self.spectrum_plot.clear_average()
        self.spectrum_plot.clear_baseline()

    def on_controller_sample_rate_changed(self) -> None:
        try:
            self.controller.data_storage.reset()
            self.spectrum_plot.clear_plot()
            self.spectrum_plot.clear_peak_hold_max()
            self.spectrum_plot.clear_peak_hold_min()
            self.spectrum_plot.clear_average()
            self.spectrum_plot.recalculate_plot(self.controller.data_storage)
        except Exception:
            pass

    def on_main_curve_toggled(self, checked: bool) -> None:
        self.spectrum_plot.main_curve = checked
        if getattr(self.spectrum_plot.curve, "xData", None) is None:
            self.spectrum_plot.update_plot(self.controller.data_storage)
        self.spectrum_plot.curve.setVisible(checked)
        if hasattr(self.spectrum_plot, "curve_fill"):
            self.spectrum_plot.curve_fill.setVisible(
                checked and not self.spectrum_plot.subtract_baseline
            )

    def on_max_hold_toggled(self, checked: bool) -> None:
        self.spectrum_plot.peak_hold_max = bool(checked)
        self.controller.data_storage.set_compute_peak_max_enabled(bool(checked))
        self.spectrum_plot.update_peak_hold_max(self.controller.data_storage, force=True)

    def on_min_hold_toggled(self, checked: bool) -> None:
        self.spectrum_plot.peak_hold_min = bool(checked)
        self.controller.data_storage.set_compute_peak_min_enabled(bool(checked))
        self.spectrum_plot.update_peak_hold_min(self.controller.data_storage, force=True)

    def on_average_toggled(self, checked: bool) -> None:
        self.spectrum_plot.average = bool(checked)
        self.controller.data_storage.set_compute_average_enabled(bool(checked))
        self.spectrum_plot.update_average(self.controller.data_storage, force=True)

    def on_smoothing_toggled(self, checked: bool) -> None:
        try:
            self.controller.data_storage.set_smooth(bool(checked))
        except Exception:
            pass
        self.spectrum_plot.update_plot(self.controller.data_storage, force=True)

    def on_persistence_toggled(self, checked: bool) -> None:
        self.spectrum_plot.persistence = bool(checked)
        if checked:
            self.spectrum_plot.recalculate_persistence(self.controller.data_storage)
        else:
            self.spectrum_plot.clear_persistence()

    def on_baseline_toggled(self, checked: bool) -> None:
        self.spectrum_plot.baseline = bool(checked)
        self.spectrum_plot.update_baseline(self.controller.data_storage, force=True)

    def on_subtract_baseline_toggled(self, checked: bool) -> None:
        ds = self.controller.data_storage
        if checked and (getattr(ds, "baseline", None) is None or getattr(ds, "baseline_x", None) is None):
            self.spectrum_plot.snapshot_baseline_from(ds, window_pts=151)
            if hasattr(self.main_window, "baselineCheckBox"):
                self.main_window.baselineCheckBox.setChecked(True)

        self.spectrum_plot.subtract_baseline = bool(checked)
        self.spectrum_plot.update_plot(ds, force=True)

    def on_baseline_snapshot(self) -> None:
        self.spectrum_plot.snapshot_baseline_from(self.controller.data_storage)
        try:
            if getattr(self.main_window, "baselineCheckBox", None) and self.main_window.baselineCheckBox.isChecked():
                self.spectrum_plot.update_baseline(self.controller.data_storage, force=True)
        except Exception:
            pass

    def on_colors_clicked(self) -> None:
        current = QtGui.QColor(self.spectrum_plot.main_color)
        color = QtGui.QColorDialog.getColor(current, self.main_window, "Main curve color")
        if color.isValid():
            self.spectrum_plot.main_color = pg.mkColor(color)
            self.spectrum_plot.main_fill_brush = pg.mkBrush(
                color.red() // 3,
                color.green() // 3,
                color.blue() // 3,
                120,
            )
            self.spectrum_plot.set_colors()
            self.spectrum_plot.update_plot(self.controller.data_storage, force=True)
