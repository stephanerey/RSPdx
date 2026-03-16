"""Runtime coordination for receivers and their worker threads."""

from __future__ import annotations

from PyQt5 import QtCore, QtGui, QtWidgets

from src.core.receiver import Receiver
from src.threading_utils.thread_manager import ManagedTaskStatus


class ReceiverRuntimeCoordinator(QtCore.QObject):
    """Manage receiver lifecycle, activation, and thread ownership."""

    request_overlay_update = QtCore.pyqtSignal(str, float, float)
    receiver_perf_updated = QtCore.pyqtSignal(dict)
    receiver_closed = QtCore.pyqtSignal(str)

    def __init__(
        self,
        main_window: QtWidgets.QMainWindow,
        controller,
        receivers_ui,
        rx_mgr,
        spectrum_widget,
        constellation_widget,
        iqctrl_checkbox,
        thread_manager=None,
    ) -> None:
        super().__init__(main_window)
        self.main_window = main_window
        self.controller = controller
        self.receivers_ui = receivers_ui
        self.rx_mgr = rx_mgr
        self.spectrum_widget = spectrum_widget
        self.constellation_widget = constellation_widget
        self.iqctrl_checkbox = iqctrl_checkbox
        self.thread_manager = thread_manager
        self._receiver_threads: dict[str, QtCore.QThread] = {}
        self.active_rx = None
        self.request_overlay_update.connect(
            self._apply_overlay_update,
            type=QtCore.Qt.QueuedConnection,
        )

    def close_rx(self, rx) -> None:
        """Stop a receiver worker, release its thread, and remove it from the runtime."""
        self.deactivate_rx(rx)
        try:
            if hasattr(rx, "_thread") and rx._thread is not None:
                try:
                    QtCore.QMetaObject.invokeMethod(rx, "shutdown", QtCore.Qt.BlockingQueuedConnection)
                except Exception:
                    pass
                rx._thread.quit()
                rx._thread.wait(500)
        except Exception:
            pass

        thread_name = getattr(rx, "_thread_name", None)
        if self.thread_manager is not None and thread_name:
            self.thread_manager.unregister_external_thread(
                thread_name,
                status=ManagedTaskStatus.STOPPED,
            )

        self._receiver_threads.pop(rx.name, None)
        self.rx_mgr.remove(rx.name)
        if self.active_rx is rx:
            self.active_rx = None
        self.receiver_closed.emit(str(rx.name))

    def deactivate_rx(self, rx) -> None:
        """Disconnect a receiver from shared UI signals and the SDR IQ stream."""
        if rx is None:
            return
        try:
            self.spectrum_widget.receiver_frequency_changed.disconnect(rx.set_selected_frequency)
        except Exception:
            pass
        try:
            self.spectrum_widget.receiver_bandwidth_changed.disconnect(rx.set_bandwidth)
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
            rx.iq_out.disconnect(self.constellation_widget.update_plot)
        except Exception:
            pass

    def activate_rx(self, rx) -> None:
        """Make a receiver the current UI target for tuning, plots, and controls."""
        if self.active_rx not in (None, rx):
            self.deactivate_rx(self.active_rx)

        try:
            self.spectrum_widget.receiver_frequency_changed.disconnect(rx.set_selected_frequency)
        except Exception:
            pass
        try:
            self.spectrum_widget.receiver_bandwidth_changed.disconnect(rx.set_bandwidth)
        except Exception:
            pass
        try:
            self.spectrum_widget.receiver_frequency_changed.connect(
                rx.set_selected_frequency,
                type=QtCore.Qt.UniqueConnection,
            )
        except TypeError:
            pass
        try:
            self.spectrum_widget.receiver_bandwidth_changed.connect(
                rx.set_bandwidth,
                type=QtCore.Qt.UniqueConnection,
            )
        except TypeError:
            pass

        try:
            if hasattr(self.controller, "iq_block"):
                try:
                    self.controller.iq_block.disconnect(rx.process_block)
                except Exception:
                    pass
                self.controller.iq_block.connect(rx.process_block, type=QtCore.Qt.UniqueConnection)
            else:
                try:
                    self.controller.new_data.disconnect(rx.process_block)
                except Exception:
                    pass
                self.controller.new_data.connect(rx.process_block, type=QtCore.Qt.UniqueConnection)
        except TypeError:
            pass

        try:
            try:
                rx.iq_out.disconnect(self.constellation_widget.update_plot)
            except Exception:
                pass
            rx.iq_out.connect(
                self.constellation_widget.update_plot,
                type=QtCore.Qt.UniqueConnection,
            )
        except TypeError:
            pass

        self.spectrum_widget.ensure_rx_overlay(
            rx.name,
            rx.ui_color,
            rx.selected_freq,
            rx.bandwidth,
            active=True,
        )
        self.spectrum_widget.set_active_rx(rx.name)
        self.spectrum_widget.update_rx_overlay(rx.name, rx.selected_freq, rx.bandwidth)
        self.spectrum_widget.set_selection_color(rx.ui_color)

        self.active_rx = rx
        try:
            self.iqctrl_checkbox.blockSignals(True)
            self.iqctrl_checkbox.setChecked(bool(getattr(rx, "iq_correction_enabled", True)))
        finally:
            self.iqctrl_checkbox.blockSignals(False)

    def add_new_receiver(
        self,
        name: str | None = None,
        f_hz: float | None = None,
        bw_hz: float = 25e3,
        enable_costas: bool = False,
        make_current: bool = True,
    ):
        """Create a receiver worker, attach it to its own thread, and register UI wiring."""
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
            parent=None,
        )

        rx_thread = QtCore.QThread(self.main_window)
        rx_thread.setObjectName(f"ReceiverThread-{name}")
        rx._thread = rx_thread
        rx._thread_name = f"Receiver:{name}"
        rx.moveToThread(rx_thread)
        rx_thread.finished.connect(rx.deleteLater)
        if self.thread_manager is not None:
            rx_thread.started.connect(
                lambda thread_name=rx._thread_name: self.thread_manager.register_external_thread(thread_name)
            )
            rx_thread.finished.connect(
                lambda thread_name=rx._thread_name: self.thread_manager.unregister_external_thread(
                    thread_name,
                    status=ManagedTaskStatus.FINISHED,
                )
            )
        rx_thread.start()
        self._receiver_threads[rx.name] = rx_thread

        rx.iq_correction_enabled = bool(self.iqctrl_checkbox.isChecked())
        rx._iq_rho = 0.0 + 0.0j
        self.rx_mgr.add(rx)

        try:
            self.controller.sample_rate_about_to_change.connect(
                rx.on_sample_rate_about_to_change,
                type=QtCore.Qt.QueuedConnection | QtCore.Qt.UniqueConnection,
            )
        except TypeError:
            pass
        try:
            self.controller.sample_rate_changed.connect(
                rx.set_sample_rate,
                type=QtCore.Qt.QueuedConnection | QtCore.Qt.UniqueConnection,
            )
        except TypeError:
            pass

        rx.ui_color = self._next_rx_color()
        rx.frequency_changed.connect(
            lambda f, r=rx: self.request_overlay_update.emit(r.name, float(f), float(r.bandwidth))
            if r is self.active_rx else None,
            type=QtCore.Qt.QueuedConnection,
        )
        rx.bandwidth_changed.connect(
            lambda bw, r=rx: self.request_overlay_update.emit(r.name, float(r.selected_freq), float(bw))
            if r is self.active_rx else None,
            type=QtCore.Qt.QueuedConnection,
        )
        rx.perf_updated.connect(
            self._forward_receiver_perf,
            type=QtCore.Qt.QueuedConnection,
        )

        self.receivers_ui.add_tab_for_rx(rx, make_current=make_current)
        self.spectrum_widget.ensure_rx_overlay(
            rx.name,
            rx.ui_color,
            rx.selected_freq,
            rx.bandwidth,
            active=make_current,
        )

        if make_current:
            self.activate_rx(rx)
        return rx

    def shutdown(self) -> None:
        """Close all receivers and stop their worker threads."""
        for rx in list(self.rx_mgr.all()):
            self.close_rx(rx)

    def reset_runtime_stats(self) -> None:
        """Ask each receiver worker to clear its runtime telemetry counters."""
        for rx in list(self.rx_mgr.all()):
            try:
                QtCore.QMetaObject.invokeMethod(
                    rx,
                    "reset_runtime_stats",
                    QtCore.Qt.QueuedConnection,
                )
            except Exception:
                pass

    def _next_rx_color(self):
        """Pick a stable tab/overlay color for the next created receiver."""
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

    @QtCore.pyqtSlot(str, float, float)
    def _apply_overlay_update(self, rx_name: str, frequency_hz: float, bandwidth_hz: float) -> None:
        """Apply overlay updates only for the currently active receiver."""
        if self.active_rx is None or self.active_rx.name != rx_name:
            return
        self.spectrum_widget.update_rx_overlay(rx_name, frequency_hz, bandwidth_hz)

    @QtCore.pyqtSlot(dict)
    def _forward_receiver_perf(self, perf: dict) -> None:
        """Relay receiver telemetry to the diagnostics UI on the GUI thread."""
        self.receiver_perf_updated.emit(perf)
