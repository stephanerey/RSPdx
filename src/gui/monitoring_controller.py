"""Helpers for monitoring docks and menu entries in the main window."""

from __future__ import annotations

from PyQt5 import QtCore, QtWidgets

from src.gui.log_viewer_ui import LogViewerDock
from src.gui.threads_ui import ThreadsDock


class MonitoringDockController:
    """Attach monitoring docks to the main window and expose menu actions."""

    def __init__(
        self,
        main_window: QtWidgets.QMainWindow,
        thread_manager=None,
        sdr_controller=None,
        receiver_runtime=None,
    ) -> None:
        self.main_window = main_window
        self.thread_manager = thread_manager
        self.sdr_controller = sdr_controller
        self.receiver_runtime = receiver_runtime
        self.threads_dock = None
        self.log_viewer_dock = None
        self.menu_view = None

    def setup(self) -> None:
        """Create monitoring docks and register their menu entries."""
        self._setup_docks()
        self._setup_menu()

    def _setup_docks(self) -> None:
        """Instantiate the diagnostics and log docks and place them in the window."""
        if self.thread_manager is not None:
            self.threads_dock = ThreadsDock(
                self.thread_manager,
                self.main_window,
                sdr_controller=self.sdr_controller,
                receiver_runtime=self.receiver_runtime,
            )
            self.main_window.addDockWidget(QtCore.Qt.BottomDockWidgetArea, self.threads_dock)
        else:
            self.threads_dock = None

        self.log_viewer_dock = LogViewerDock(self.main_window)
        self.main_window.addDockWidget(QtCore.Qt.BottomDockWidgetArea, self.log_viewer_dock)

        if self.threads_dock is not None:
            self.main_window.tabifyDockWidget(self.threads_dock, self.log_viewer_dock)
            self.threads_dock.hide()
        self.log_viewer_dock.hide()

    def _setup_menu(self) -> None:
        """Create the View menu entries used to open diagnostics windows."""
        self.menu_view = QtWidgets.QMenu("View", self.main_window)
        self.menu_view.setObjectName("menu_View")

        if hasattr(self.main_window, "menu_Help"):
            self.main_window.menubar.insertMenu(self.main_window.menu_Help.menuAction(), self.menu_view)
        else:
            self.main_window.menubar.addAction(self.menu_view.menuAction())

        if self.threads_dock is not None:
            threads_action = QtWidgets.QAction("Thread Manager", self.main_window)
            threads_action.triggered.connect(self.show_threads_dock)
            self.menu_view.addAction(threads_action)

        logs_action = QtWidgets.QAction("Logs", self.main_window)
        logs_action.triggered.connect(self.show_logs_dock)
        self.menu_view.addAction(logs_action)

    def show_threads_dock(self) -> None:
        """Open the thread diagnostics dock as a floating window."""
        if self.threads_dock is None:
            return
        self._present_monitoring_dock(self.threads_dock, QtCore.QSize(760, 320))

    def show_logs_dock(self) -> None:
        """Open the log viewer dock as a floating window."""
        self._present_monitoring_dock(self.log_viewer_dock, QtCore.QSize(900, 420))

    @staticmethod
    def _present_monitoring_dock(dock: QtWidgets.QDockWidget, size_hint: QtCore.QSize) -> None:
        """Show a dock as a floating tool window and bring it to the foreground."""
        dock.setFloating(True)
        dock.resize(size_hint)
        dock.show()
        dock.raise_()
        dock.activateWindow()
