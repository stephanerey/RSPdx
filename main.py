import sys
import logging
from PyQt5 import QtWidgets, QtCore

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)

from src.threading.thread_manager import ThreadManager
from src.gui.main_ui import SDRGUI


def _excepthook(exc_type, exc_value, exc_tb):
    # ordre correct: (type, value, traceback)
    logging.exception("Unhandled exception", exc_info=(exc_type, exc_value, exc_tb))
    try:
        QtWidgets.QMessageBox.critical(
            None,
            "Unhandled exception",
            f"{exc_type.__name__}: {exc_value}"
        )
    except Exception:
        pass

def main():
    QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)
    QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps, True)

    app = QtWidgets.QApplication(sys.argv)
    app.setOrganizationName("PLDesign")
    app.setApplicationName("RSPdx")

    tm = ThreadManager()
    window = SDRGUI(thread_manager=tm)
    window.show()

    sys.excepthook = _excepthook

    def on_quit():
        try:
            window.shutdown()
        finally:
            tm.stop_all_threads()
    app.aboutToQuit.connect(on_quit)

    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
