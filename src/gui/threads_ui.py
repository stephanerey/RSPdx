"""Thread diagnostics widgets for the RSPdx GUI."""

from __future__ import annotations

import csv
from collections import deque
import time

from PyQt5 import QtCore, QtGui, QtWidgets
import pyqtgraph as pg

from src.threading_utils.thread_manager import ThreadManager
from src.utils.misc import human_time


class DiagnosticsTable(QtWidgets.QTableWidget):
    """Read-only table used by the diagnostics tabs."""

    HEADERS = ["Name", "Origin", "Status", "Starts", "Last", "Total", "Last error"]

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(0, len(self.HEADERS), parent)
        self.setHorizontalHeaderLabels(self.HEADERS)
        self.horizontalHeader().setStretchLastSection(True)
        self.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeToContents)
        self.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)

    def populate(self, diagnostics: list[tuple[str, dict]]) -> None:
        self.setRowCount(len(diagnostics))
        for row, (name, info) in enumerate(diagnostics):
            values = [
                name,
                info.get("origin", "-"),
                str(info.get("status", "-")),
                str(info.get("start_count", 0)),
                self._format_duration(info.get("last_duration_s")),
                self._format_duration(info.get("total_runtime_s")),
                info.get("last_error") or "-",
            ]
            for column, value in enumerate(values):
                self.setItem(row, column, QtWidgets.QTableWidgetItem(value))

    @staticmethod
    def _format_duration(value: float | None) -> str:
        if value is None:
            return "-"
        return human_time(value)


class MetricBarDelegate(QtWidgets.QStyledItemDelegate):
    """Render a compact bar inside a table cell while keeping the numeric label."""

    def __init__(
        self,
        scale_max: float,
        color: str,
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.scale_max = float(max(1e-9, scale_max))
        self._bar_color = QtGui.QColor(color)
        self._track_color = QtGui.QColor("#2a2a2a")
        self._text_color = QtGui.QColor("#f0f0f0")

    def paint(self, painter, option, index) -> None:
        bar_value = index.data(QtCore.Qt.UserRole)
        if bar_value is None:
            super().paint(painter, option, index)
            return

        text = str(index.data(QtCore.Qt.DisplayRole) or "")
        value = float(max(0.0, min(float(bar_value), self.scale_max)))
        bar_color = index.data(QtCore.Qt.UserRole + 1)
        if bar_color is not None:
            bar_color = QtGui.QColor(str(bar_color))
        else:
            bar_color = self._bar_color

        painter.save()
        if option.state & QtWidgets.QStyle.State_Selected:
            painter.fillRect(option.rect, option.palette.highlight())
        else:
            painter.fillRect(option.rect, option.palette.base())

        bar_rect = option.rect.adjusted(4, 5, -4, -5)
        painter.setPen(QtCore.Qt.NoPen)
        painter.setBrush(self._track_color)
        painter.drawRoundedRect(bar_rect, 3.0, 3.0)

        fill_width = int(bar_rect.width() * (value / self.scale_max))
        if fill_width > 0:
            fill_rect = QtCore.QRect(bar_rect.left(), bar_rect.top(), fill_width, bar_rect.height())
            painter.setBrush(bar_color)
            painter.drawRoundedRect(fill_rect, 3.0, 3.0)

        painter.setPen(self._text_color if not (option.state & QtWidgets.QStyle.State_Selected) else option.palette.highlightedText().color())
        painter.drawText(option.rect.adjusted(8, 0, -8, 0), QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft, text)
        painter.restore()


class PerformanceHistoryWidget(QtWidgets.QWidget):
    """Display a rolling history of SDR performance metrics."""

    def __init__(self, parent: QtWidgets.QWidget | None = None, max_points: int = 180) -> None:
        super().__init__(parent)
        self._max_points = int(max_points)
        self._t0 = time.monotonic()
        self._times = deque(maxlen=max_points)
        self._iq_mbit = deque(maxlen=max_points)
        self._eff_ratio = deque(maxlen=max_points)
        self._blocks = deque(maxlen=max_points)
        self._fft_avg = deque(maxlen=max_points)
        self._fft_load = deque(maxlen=max_points)
        self._history_rows = deque(maxlen=max_points)

        self.status_label = QtWidgets.QLabel(
            "Mode: -- | IQ throughput: -- | Timeouts: -- | Errors: -- | NFFT: -- | Buffer: --"
        )
        self.status_label.setWordWrap(True)

        self.iq_plot = self._make_plot("IQ Throughput", "Mbit/s", "#39b8d6")
        self.eff_plot = self._make_plot("Effective Sample Rate", "% of target", "#7bd66a")
        self.blocks_plot = self._make_plot("IQ Blocks Rate", "blocks/s", "#f2c14e")
        self.fft_plot = self._make_plot("FFT Compute Avg", "ms", "#ff7f66")
        self.fft_load_plot = self._make_plot("FFT Load Estimate", "% of 1 s", "#c084fc")

        self.iq_curve = self.iq_plot.plot(pen=pg.mkPen("#39b8d6", width=2))
        self.eff_curve = self.eff_plot.plot(pen=pg.mkPen("#7bd66a", width=2))
        self.blocks_curve = self.blocks_plot.plot(pen=pg.mkPen("#f2c14e", width=2))
        self.fft_curve = self.fft_plot.plot(pen=pg.mkPen("#ff7f66", width=2))
        self.fft_load_curve = self.fft_load_plot.plot(pen=pg.mkPen("#c084fc", width=2))

        plots = QtWidgets.QGridLayout()
        plots.addWidget(self.iq_plot, 0, 0)
        plots.addWidget(self.eff_plot, 0, 1)
        plots.addWidget(self.blocks_plot, 1, 0)
        plots.addWidget(self.fft_plot, 1, 1)
        plots.addWidget(self.fft_load_plot, 2, 0, 1, 2)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.status_label)
        layout.addLayout(plots)

    def update_metrics(self, perf: dict) -> None:
        """Append one SDR telemetry sample and refresh the history plots."""
        t = time.monotonic() - self._t0
        fft_load_pct = float(perf.get("fft_rate_hz", 0.0)) * float(perf.get("fft_avg_ms", 0.0)) / 10.0
        self._times.append(t)
        self._iq_mbit.append(float(perf.get("iq_mbit_s", 0.0)))
        self._eff_ratio.append(float(perf.get("sample_rate_ratio_pct", 0.0)))
        self._blocks.append(float(perf.get("block_rate_hz", 0.0)))
        self._fft_avg.append(float(perf.get("fft_avg_ms", 0.0)))
        self._fft_load.append(fft_load_pct)
        self._history_rows.append(
            {
                "time_s": t,
                "mode": perf.get("mode", "--"),
                "iq_mbit_s": float(perf.get("iq_mbit_s", 0.0)),
                "sample_rate_effective_hz": float(perf.get("sample_rate_effective_hz", 0.0)),
                "sample_rate_ratio_pct": float(perf.get("sample_rate_ratio_pct", 0.0)),
                "iq_block_rate_hz": float(perf.get("block_rate_hz", 0.0)),
                "fft_rate_hz": float(perf.get("fft_rate_hz", 0.0)),
                "fft_avg_ms": float(perf.get("fft_avg_ms", 0.0)),
                "fft_load_pct": float(fft_load_pct),
                "time_outs": int(perf.get("time_outs", 0)),
                "stream_errors": int(perf.get("stream_errors", 0)),
                "fft_size": int(perf.get("fft_size", 0)),
                "buffer_size": int(perf.get("buffer_size", 0)),
            }
        )

        x = list(self._times)
        self.iq_curve.setData(x, list(self._iq_mbit))
        self.eff_curve.setData(x, list(self._eff_ratio))
        self.blocks_curve.setData(x, list(self._blocks))
        self.fft_curve.setData(x, list(self._fft_avg))
        self.fft_load_curve.setData(x, list(self._fft_load))

        self.status_label.setText(
            "Mode: "
            f"{perf.get('mode', '--')} | "
            f"IQ throughput: {float(perf.get('iq_mbit_s', 0.0)):.1f} Mbit/s | "
            f"Timeouts: {int(perf.get('time_outs', 0))} | "
            f"Errors: {int(perf.get('stream_errors', 0))} | "
            f"NFFT: {int(perf.get('fft_size', 0))} | "
            f"Buffer: {int(perf.get('buffer_size', 0))}"
        )

    def reset_history(self) -> None:
        """Clear the stored SDR telemetry history and reset all plots."""
        self._t0 = time.monotonic()
        self._times.clear()
        self._iq_mbit.clear()
        self._eff_ratio.clear()
        self._blocks.clear()
        self._fft_avg.clear()
        self._fft_load.clear()
        self._history_rows.clear()
        for curve in (
            self.iq_curve,
            self.eff_curve,
            self.blocks_curve,
            self.fft_curve,
            self.fft_load_curve,
        ):
            curve.setData([], [])
        self.status_label.setText(
            "Mode: -- | IQ throughput: -- | Timeouts: -- | Errors: -- | NFFT: -- | Buffer: --"
        )

    def export_history_csv(self, file_path: str) -> None:
        """Export the current SDR telemetry history to a CSV file."""
        rows = list(self._history_rows)
        with open(file_path, "w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=[
                    "time_s",
                    "mode",
                    "iq_mbit_s",
                    "sample_rate_effective_hz",
                    "sample_rate_ratio_pct",
                    "iq_block_rate_hz",
                    "fft_rate_hz",
                    "fft_avg_ms",
                    "fft_load_pct",
                    "time_outs",
                    "stream_errors",
                    "fft_size",
                    "buffer_size",
                ],
            )
            writer.writeheader()
            writer.writerows(rows)

    @staticmethod
    def _make_plot(title: str, y_label: str, color: str):
        plot = pg.PlotWidget()
        plot.setBackground("#202124")
        plot.showGrid(x=True, y=True, alpha=0.25)
        plot.setTitle(title, color="w")
        plot.setLabel("left", y_label)
        plot.setLabel("bottom", "time (s)")
        plot.getAxis("left").setTextPen(color)
        plot.getAxis("bottom").setTextPen("#dddddd")
        return plot


class ReceiverTelemetryWidget(QtWidgets.QWidget):
    """Display live telemetry for each receiver worker."""

    ALERT_COLORS = {
        "ok": "#39b8d6",
        "warning": "#d99a2b",
        "critical": "#d64b4b",
    }

    COL_AUDIO_RMS = 8
    COL_AUDIO_PEAK = 11
    COL_AUDIO_BUFFER = 12
    COL_LOW_WATER = 13
    COL_UNDERRUNS = 14
    COL_OVERFLOWS = 15
    COL_CLIPS = 16

    HEADERS = [
        "Name",
        "Demod",
        "Audio",
        "Freq (MHz)",
        "BW (kHz)",
        "BB rate (kS/s)",
        "IQ blocks/s",
        "Proc avg (ms)",
        "Proc max (ms)",
        "Demod avg (ms)",
        "Audio RMS",
        "Audio peak",
        "Audio buffer (%)",
        "Low water (%)",
        "Underruns",
        "Overflows",
        "Clips",
    ]

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self._rows: dict[str, dict] = {}
        self.summary_label = QtWidgets.QLabel("No receiver telemetry recorded yet.")
        self.summary_label.setWordWrap(True)
        self.table = QtWidgets.QTableWidget(0, len(self.HEADERS), self)
        self.table.setHorizontalHeaderLabels(self.HEADERS)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeToContents)
        self.table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.table.setItemDelegateForColumn(
            self.COL_AUDIO_RMS,
            MetricBarDelegate(scale_max=1.0, color="#55c271", parent=self.table),
        )
        self.table.setItemDelegateForColumn(
            self.COL_AUDIO_BUFFER,
            MetricBarDelegate(scale_max=100.0, color="#39b8d6", parent=self.table),
        )

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.summary_label)
        layout.addWidget(self.table)

    @classmethod
    def _buffer_alert_level(cls, buffer_pct: float) -> str:
        if buffer_pct < 8.0 or buffer_pct > 90.0:
            return "critical"
        if buffer_pct < 15.0 or buffer_pct > 85.0:
            return "warning"
        return "ok"

    @classmethod
    def _peak_alert_level(cls, peak: float) -> str:
        if peak >= 0.98:
            return "critical"
        if peak >= 0.90:
            return "warning"
        return "ok"

    @classmethod
    def _proc_alert_level(cls, process_avg_ms: float, block_rate_hz: float) -> str:
        if block_rate_hz <= 1e-9:
            return "ok"
        budget_ms = 1000.0 / block_rate_hz
        ratio = process_avg_ms / max(1e-9, budget_ms)
        if ratio >= 0.95:
            return "critical"
        if ratio >= 0.75:
            return "warning"
        return "ok"

    def _apply_alert_style(self, item: QtWidgets.QTableWidgetItem, level: str, tooltip: str) -> None:
        item.setToolTip(tooltip)
        if level == "warning":
            item.setBackground(QtGui.QColor("#4d3a12"))
            item.setForeground(QtGui.QColor("#ffd38a"))
        elif level == "critical":
            item.setBackground(QtGui.QColor("#512020"))
            item.setForeground(QtGui.QColor("#ffb0b0"))

    def update_metrics(self, perf: dict) -> None:
        """Store one receiver telemetry sample and rebuild the table view."""
        name = str(perf.get("name", "")).strip()
        if not name:
            return
        self._rows[name] = dict(perf)
        self._rebuild_table()

    def _rebuild_table(self) -> None:
        """Re-render the receiver telemetry table from the current cached rows."""
        ordered = sorted(self._rows.items())
        self.table.setRowCount(len(ordered))
        for row, (rx_name, info) in enumerate(ordered):
            block_rate = float(info.get("iq_block_rate_hz", 0.0))
            process_avg_ms = float(info.get("process_avg_ms", 0.0))
            process_max_ms = float(info.get("process_max_ms", 0.0))
            audio_peak = float(info.get("audio_peak", 0.0))
            audio_buffer = float(info.get("audio_buffer_fill_pct", 0.0))
            low_water = float(info.get("audio_low_water_pct", audio_buffer))
            underruns = int(info.get("audio_underruns", 0))
            overflows = int(info.get("audio_overflows", 0))
            clips = int(info.get("audio_clip_events", 0))
            proc_alert = self._proc_alert_level(process_avg_ms, block_rate)
            proc_max_alert = self._proc_alert_level(process_max_ms, block_rate)
            peak_alert = self._peak_alert_level(audio_peak)
            buffer_alert = self._buffer_alert_level(audio_buffer)
            low_water_alert = self._buffer_alert_level(low_water)
            values = [
                rx_name,
                str(info.get("demod_mode", "--")),
                "On" if bool(info.get("audio_enabled", False)) else "Off",
                f"{float(info.get('selected_freq_hz', 0.0)) / 1e6:.6f}",
                f"{float(info.get('bandwidth_hz', 0.0)) / 1e3:.1f}",
                f"{float(info.get('baseband_ksample_s', 0.0)):.1f}",
                f"{float(info.get('iq_block_rate_hz', 0.0)):.1f}",
                f"{float(info.get('process_avg_ms', 0.0)):.3f}",
                f"{float(info.get('process_max_ms', 0.0)):.3f}",
                f"{float(info.get('demod_avg_ms', 0.0)):.3f}",
                f"{float(info.get('audio_rms', 0.0)):.4f}",
                f"{float(info.get('audio_peak', 0.0)):.4f}",
                f"{float(info.get('audio_buffer_fill_pct', 0.0)):.1f}",
                f"{float(info.get('audio_low_water_pct', audio_buffer)):.1f}",
                str(underruns),
                str(overflows),
                str(clips),
            ]
            for column, value in enumerate(values):
                item = QtWidgets.QTableWidgetItem(value)
                if column == self.COL_AUDIO_RMS:
                    item.setData(QtCore.Qt.UserRole, float(info.get("audio_rms", 0.0)))
                    item.setData(QtCore.Qt.UserRole + 1, self.ALERT_COLORS["ok"])
                elif column == self.COL_AUDIO_BUFFER:
                    item.setData(QtCore.Qt.UserRole, audio_buffer)
                    item.setData(QtCore.Qt.UserRole + 1, self.ALERT_COLORS[buffer_alert])
                    if buffer_alert != "ok":
                        self._apply_alert_style(
                            item,
                            buffer_alert,
                            "Audio buffer outside the preferred range. Low values may underrun; high values may increase latency.",
                        )
                elif column == self.COL_AUDIO_PEAK:
                    if peak_alert != "ok":
                        self._apply_alert_style(
                            item,
                            peak_alert,
                            "Audio peak is close to saturation or clipping.",
                        )
                elif column == 7:
                    if proc_alert != "ok":
                        self._apply_alert_style(
                            item,
                            proc_alert,
                            "Receiver processing time is approaching the per-block realtime budget.",
                        )
                elif column == 8:
                    if proc_max_alert != "ok":
                        self._apply_alert_style(
                            item,
                            proc_max_alert,
                            "Receiver worst-case processing time is close to the per-block realtime budget.",
                        )
                elif column == self.COL_LOW_WATER:
                    if low_water_alert != "ok":
                        self._apply_alert_style(
                            item,
                            low_water_alert,
                            "Lowest observed audio buffer fill. Low values indicate poor realtime margin.",
                        )
                elif column == self.COL_UNDERRUNS and underruns > 0:
                    self._apply_alert_style(
                        item,
                        "critical",
                        "Audio callback requested more frames than available in the buffer.",
                    )
                elif column == self.COL_OVERFLOWS and overflows > 0:
                    self._apply_alert_style(
                        item,
                        "warning",
                        "Audio producer could not push all generated samples into the buffer.",
                    )
                elif column == self.COL_CLIPS and clips > 0:
                    self._apply_alert_style(
                        item,
                        "warning" if clips < 10 else "critical",
                        "Audio samples reached the clipping or near-clipping threshold.",
                    )
                self.table.setItem(row, column, item)

        active = sum(1 for info in self._rows.values() if bool(info.get("audio_enabled", False)))
        self.summary_label.setText(
            f"Receivers tracked: {len(self._rows)} | Audio active: {active}"
        )

    def reset(self) -> None:
        """Clear all cached receiver telemetry and empty the table."""
        self._rows.clear()
        self.table.setRowCount(0)
        self.summary_label.setText("No receiver telemetry recorded yet.")

    def remove_receiver(self, name: str) -> None:
        """Remove a closed receiver from the telemetry table."""
        key = str(name).strip()
        if not key:
            return
        self._rows.pop(key, None)
        self._rebuild_table()


class ThreadsWidget(QtWidgets.QWidget):
    """Display the state of managed and tracked threads."""

    TAB_FILTERS = [
        ("All", None),
        ("Running", {"running"}),
        ("Stopped", {"stopped", "finished"}),
        ("Errors", {"failed"}),
    ]

    def __init__(
        self,
        thread_manager: ThreadManager,
        parent: QtWidgets.QWidget | None = None,
        sdr_controller=None,
        receiver_runtime=None,
    ) -> None:
        super().__init__(parent)
        self.thread_manager = thread_manager
        self.sdr_controller = sdr_controller
        self.receiver_runtime = receiver_runtime
        self._tables: dict[str, DiagnosticsTable] = {}

        self.summary_label = QtWidgets.QLabel("No thread activity recorded yet.")
        self.summary_label.setWordWrap(True)
        self.perf_label = QtWidgets.QLabel(
            "IQ throughput: -- | eff_fs: -- | IQ blocks/s: -- | FFT compute avg: --"
        )
        self.perf_label.setWordWrap(True)

        self.tabs = QtWidgets.QTabWidget(self)
        for label, _ in self.TAB_FILTERS:
            table = DiagnosticsTable(self.tabs)
            self._tables[label] = table
            self.tabs.addTab(table, label)
        self.table = self._tables["All"]
        self.performance_widget = PerformanceHistoryWidget(self.tabs)
        self.tabs.addTab(self.performance_widget, "Performance")
        self.receiver_widget = ReceiverTelemetryWidget(self.tabs)
        self.tabs.addTab(self.receiver_widget, "Receivers")

        self.refresh_button = QtWidgets.QPushButton("Refresh")
        self.summary_button = QtWidgets.QPushButton("Summary")
        self.reset_perf_button = QtWidgets.QPushButton("Reset perf history")
        self.export_perf_button = QtWidgets.QPushButton("Export perf CSV")
        self.summary_button.clicked.connect(self._show_summary)
        self.refresh_button.clicked.connect(self.refresh)
        self.reset_perf_button.clicked.connect(self._reset_perf_history)
        self.export_perf_button.clicked.connect(self._export_perf_history)

        buttons = QtWidgets.QHBoxLayout()
        buttons.addWidget(self.refresh_button)
        buttons.addWidget(self.summary_button)
        buttons.addWidget(self.reset_perf_button)
        buttons.addWidget(self.export_perf_button)
        buttons.addStretch(1)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.summary_label)
        layout.addWidget(self.perf_label)
        layout.addLayout(buttons)
        layout.addWidget(self.tabs)

        self._timer = QtCore.QTimer(self)
        self._timer.setInterval(1500)
        self._timer.timeout.connect(self.refresh)
        self._timer.start()

        self.thread_manager.diagnostics_changed.connect(self.refresh)
        if self.sdr_controller is not None and hasattr(self.sdr_controller, "perf_updated"):
            self.sdr_controller.perf_updated.connect(self._on_perf_updated)
        if self.receiver_runtime is not None and hasattr(self.receiver_runtime, "receiver_perf_updated"):
            self.receiver_runtime.receiver_perf_updated.connect(self._on_receiver_perf_updated)
        if self.receiver_runtime is not None and hasattr(self.receiver_runtime, "receiver_closed"):
            self.receiver_runtime.receiver_closed.connect(self._on_receiver_closed)
        self.refresh()

    @QtCore.pyqtSlot()
    def refresh(self) -> None:
        """Refresh thread diagnostics tables from the thread manager snapshot."""
        diagnostics = self.thread_manager.get_diagnostics()
        ordered = sorted(diagnostics.items())
        running = sum(1 for _, info in ordered if info["status"] == "running")
        failed = sum(1 for _, info in ordered if info["status"] == "failed")
        stopped = sum(1 for _, info in ordered if info["status"] in {"stopped", "finished"})

        self.summary_label.setText(
            "Tracked threads: "
            f"{len(ordered)} | Running: {running} | Stopped: {stopped} | Errors: {failed}"
        )

        for label, statuses in self.TAB_FILTERS:
            if statuses is None:
                subset = ordered
            else:
                subset = [(name, info) for name, info in ordered if info["status"] in statuses]
            self._tables[label].populate(subset)
            index = self.tabs.indexOf(self._tables[label])
            self.tabs.setTabText(index, f"{label} ({len(subset)})")

    def _show_summary(self) -> None:
        """Open a modal summary dialog for the current thread diagnostics."""
        QtWidgets.QMessageBox.information(
            self,
            "Thread diagnostics",
            self.thread_manager.diagnostics_summary(),
        )

    def _reset_perf_history(self) -> None:
        """Reset SDR and receiver runtime telemetry counters and clear the UI history."""
        if self.sdr_controller is not None and hasattr(self.sdr_controller, "reset_perf_stats"):
            try:
                self.sdr_controller.reset_perf_stats()
            except Exception:
                pass
        if self.receiver_runtime is not None and hasattr(self.receiver_runtime, "reset_runtime_stats"):
            try:
                self.receiver_runtime.reset_runtime_stats()
            except Exception:
                pass
        self.performance_widget.reset_history()
        self.receiver_widget.reset()
        self.perf_label.setText(
            "IQ throughput: -- | eff_fs: -- | IQ blocks/s: -- | FFT compute avg: --"
        )

    def _export_perf_history(self) -> None:
        """Prompt for a destination file and export SDR performance history as CSV."""
        file_path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "Export performance history",
            "rspdx_perf_history.csv",
            "CSV files (*.csv)",
        )
        if not file_path:
            return
        self.performance_widget.export_history_csv(file_path)

    @QtCore.pyqtSlot(dict)
    def _on_perf_updated(self, perf: dict) -> None:
        """Update the top-line SDR summary and append one telemetry sample."""
        self.perf_label.setText(
            "IQ throughput: "
            f"{float(perf.get('iq_mbit_s', 0.0)):.1f} Mbit/s | "
            f"eff_fs: {float(perf.get('sample_rate_effective_hz', 0.0)) / 1e6:.3f} MS/s "
            f"({float(perf.get('sample_rate_ratio_pct', 0.0)):.1f}%) | "
            f"IQ blocks/s: {float(perf.get('block_rate_hz', 0.0)):.1f} | "
            f"FFT compute avg: {float(perf.get('fft_avg_ms', 0.0)):.2f} ms | "
            f"timeouts: {int(perf.get('time_outs', 0))} | "
            f"errors: {int(perf.get('stream_errors', 0))}"
        )
        self.performance_widget.update_metrics(perf)

    @QtCore.pyqtSlot(dict)
    def _on_receiver_perf_updated(self, perf: dict) -> None:
        """Update the receiver telemetry tab with one receiver snapshot."""
        self.receiver_widget.update_metrics(perf)

    @QtCore.pyqtSlot(str)
    def _on_receiver_closed(self, name: str) -> None:
        """Remove a receiver from the telemetry table once its worker is closed."""
        self.receiver_widget.remove_receiver(name)


class ThreadsDock(QtWidgets.QDockWidget):
    """Dock wrapper used by the main window."""

    def __init__(
        self,
        thread_manager: ThreadManager,
        parent: QtWidgets.QWidget | None = None,
        sdr_controller=None,
        receiver_runtime=None,
    ) -> None:
        super().__init__("Threads", parent)
        self.setObjectName("ThreadsDock")
        self.setWidget(
            ThreadsWidget(
                thread_manager,
                self,
                sdr_controller=sdr_controller,
                receiver_runtime=receiver_runtime,
            )
        )
