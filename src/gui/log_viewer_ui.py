"""Log file viewer widgets for the RSPdx GUI."""

from __future__ import annotations

from pathlib import Path

from PyQt5 import QtCore, QtWidgets

from src.tools.paths import get_log_file_path


class LogViewerWidget(QtWidgets.QWidget):
    """Display the application log file with lightweight tailing."""

    def __init__(self, log_file: Path | None = None, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.log_file = Path(log_file) if log_file is not None else get_log_file_path()
        self._last_mtime = 0.0

        self.path_label = QtWidgets.QLabel(str(self.log_file))
        self.path_label.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)

        self.text_edit = QtWidgets.QPlainTextEdit(self)
        self.text_edit.setReadOnly(True)

        self.refresh_button = QtWidgets.QPushButton("Refresh")
        self.refresh_button.clicked.connect(self.refresh)
        self.follow_checkbox = QtWidgets.QCheckBox("Follow")
        self.follow_checkbox.setChecked(True)

        controls = QtWidgets.QHBoxLayout()
        controls.addWidget(self.refresh_button)
        controls.addWidget(self.follow_checkbox)
        controls.addStretch(1)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.path_label)
        layout.addLayout(controls)
        layout.addWidget(self.text_edit)

        self._timer = QtCore.QTimer(self)
        self._timer.setInterval(1500)
        self._timer.timeout.connect(self.refresh)
        self._timer.start()

        self.refresh()

    @QtCore.pyqtSlot()
    def refresh(self) -> None:
        if not self.log_file.exists():
            self.text_edit.setPlainText("Log file not created yet.")
            return

        stat = self.log_file.stat()
        if stat.st_mtime == self._last_mtime and self.text_edit.toPlainText():
            return

        self._last_mtime = stat.st_mtime
        try:
            content = self.log_file.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            self.text_edit.setPlainText(f"Unable to read log file:\n{exc}")
            return

        self.text_edit.setPlainText(content[-120_000:])
        if self.follow_checkbox.isChecked():
            scrollbar = self.text_edit.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())


class LogViewerDock(QtWidgets.QDockWidget):
    """Dock wrapper used by the main window."""

    def __init__(self, parent: QtWidgets.QWidget | None = None, log_file: Path | None = None) -> None:
        super().__init__("Logs", parent)
        self.setObjectName("LogsDock")
        self.setWidget(LogViewerWidget(log_file=log_file, parent=self))

