import logging
import os
import sys

from PyQt5 import QtCore, QtWidgets

from src.config import settings
from src.gui.main_ui import SDRGUI
from src.threading_utils.thread_manager import ThreadManager
from src.tools.paths import ensure_runtime_directories, get_log_file_path


def configure_logging() -> None:
    ensure_runtime_directories()
    log_file = get_log_file_path()
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

    session_logger = logging.getLogger("RSPdx.Session")
    session_logger.info("=" * 72)
    session_logger.info(
        "Session started | app=%s | pid=%s | log=%s",
        settings.APP_NAME,
        os.getpid(),
        log_file,
    )
    session_logger.info("=" * 72)


def _excepthook(exc_type, exc_value, exc_tb) -> None:
    logging.exception("Unhandled exception", exc_info=(exc_type, exc_value, exc_tb))
    try:
        QtWidgets.QMessageBox.critical(
            None,
            "Unhandled exception",
            f"{exc_type.__name__}: {exc_value}",
        )
    except Exception:
        pass


def main() -> None:
    configure_logging()

    QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)
    QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps, True)

    app = QtWidgets.QApplication(sys.argv)
    app.setOrganizationName(settings.APP_ORGANIZATION)
    app.setApplicationName(settings.APP_NAME)

    thread_manager = ThreadManager()
    window = SDRGUI(thread_manager=thread_manager)
    window.show()

    sys.excepthook = _excepthook

    def on_quit() -> None:
        try:
            window.shutdown()
        finally:
            thread_manager.stop_all_threads()

    app.aboutToQuit.connect(on_quit)
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
