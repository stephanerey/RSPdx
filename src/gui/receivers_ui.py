# src/gui/receivers_ui.py
from PyQt5 import QtWidgets, QtCore, QtGui
from .receiver_tab import ReceiverTabPage

class ReceiversUI(QtCore.QObject):
    """
    Encapsule la gestion du panneau 'Receivers' (QTabWidget) :
      - création/réutilisation du groupbox + TabWidget (ou dock fallback)
      - onglet “+” pour ajouter un RX
      - mapping page -> rx
      - couleur des tabs
      - signaux: activated(rx), addRequested(), closed(rx)
    """
    activated = QtCore.pyqtSignal(object)      # rx
    addRequested = QtCore.pyqtSignal()
    closed = QtCore.pyqtSignal(object)         # rx

    def __init__(self, main_window):
        super().__init__(main_window)
        self.w = main_window
        self.tab = None
        self._pages = {}  # QWidget -> rx
        self._ensure_panel()
        self._wire_signals()
        self._ensure_plus_tab()

    # — public API —
    def add_tab_for_rx(self, rx, make_current=True):
        page = ReceiverTabPage(self.w)
        page.bind(rx, self.w.spectrumPlotWidget)

        plus_idx = self._plus_tab_index()
        if plus_idx is None:
            idx = self.tab.addTab(page, rx.name)
        else:
            idx = self.tab.insertTab(plus_idx, page, rx.name)

        self._pages[page] = rx
        # couleur du tab = couleur RX
        if hasattr(rx, "ui_color"):
            self.tab.tabBar().setTabTextColor(idx, rx.ui_color)

        if make_current:
            self.tab.setCurrentIndex(idx)
        return page

    def remove_index(self, index: int):
        if index == self._plus_tab_index():  # refuse de supprimer le '+'
            return
        page = self.tab.widget(index)
        rx = self._pages.pop(page, None)
        self.tab.removeTab(index)
        if page is not None:
            page.deleteLater()
        if rx is not None:
            self.closed.emit(rx)

    def page_to_rx(self, page: QtWidgets.QWidget):
        return self._pages.get(page)

    # — internal —
    def _wire_signals(self):
        self.tab.tabBarClicked.connect(self._on_tab_clicked)
        self.tab.currentChanged.connect(self._on_current_changed)
        self.tab.tabCloseRequested.connect(self._on_close_requested)

    def _on_tab_clicked(self, index: int):
        if index == self._plus_tab_index():
            self.addRequested.emit()

    def _on_current_changed(self, index: int):
        if index == self._plus_tab_index() or index < 0:
            return
        page = self.tab.widget(index)
        rx = self._pages.get(page)
        if rx is not None:
            self.activated.emit(rx)

    def _on_close_requested(self, index: int):
        self.remove_index(index)

    def _plus_tab_index(self):
        for i in range(self.tab.count()):
            if self.tab.tabText(i) == "+":
                return i
        return None

    def _ensure_plus_tab(self):
        if self._plus_tab_index() is None:
            plus = QtWidgets.QWidget()
            plus.setObjectName("plusTab")
            self.tab.addTab(plus, "+")

    def _ensure_panel(self):
        # 1) Tab existant nommé 'receiversTabWidget' ?
        existing = self.w.findChild(QtWidgets.QTabWidget, "receiversTabWidget")
        if existing is not None:
            self.tab = existing
            self.tab.setTabsClosable(True)
            self.tab.setMovable(True)
            return

        # 2) GroupBox 'Receivers' existant ?
        receivers_box = None
        for gb in self.w.findChildren(QtWidgets.QGroupBox):
            if gb.title().strip().lower() == "receivers":
                receivers_box = gb
                break
        if receivers_box is not None:
            tw = receivers_box.findChild(QtWidgets.QTabWidget, "receiversTabWidget")
            if tw is None:
                tw = QtWidgets.QTabWidget(receivers_box)
                tw.setObjectName("receiversTabWidget")
                tw.setTabsClosable(True)
                tw.setMovable(True)
                if receivers_box.layout() is None:
                    v = QtWidgets.QVBoxLayout(receivers_box)
                else:
                    v = receivers_box.layout()
                v.addWidget(tw)
            self.tab = tw
            return

        # 3) Sinon, insérer sous 'Source' si possible
        source_box = None
        for gb in self.w.findChildren(QtWidgets.QGroupBox):
            if gb.title().strip().lower() == "source":
                source_box = gb
                break
        if source_box is not None:
            parent_layout = source_box.parentWidget().layout()
            if isinstance(parent_layout, QtWidgets.QVBoxLayout):
                box = QtWidgets.QGroupBox("Receivers", parent_layout.parentWidget())
                v = QtWidgets.QVBoxLayout(box)
                tw = QtWidgets.QTabWidget(box)
                tw.setObjectName("receiversTabWidget")
                tw.setTabsClosable(True)
                tw.setMovable(True)
                v.addWidget(tw)
                # insérer juste après 'Source'
                idx = None
                for i in range(parent_layout.count()):
                    it = parent_layout.itemAt(i)
                    if it and it.widget() is source_box:
                        idx = i; break
                insert_at = (idx + 1) if idx is not None else parent_layout.count()
                parent_layout.insertWidget(insert_at, box)
                self.tab = tw
                return

        # 4) Fallback Dock
        dock = QtWidgets.QDockWidget("Receivers", self.w)
        dock.setObjectName("ReceiversDock")
        tw = QtWidgets.QTabWidget(dock)
        tw.setObjectName("receiversTabWidget")
        tw.setTabsClosable(True)
        tw.setMovable(True)
        dock.setWidget(tw)
        self.w.addDockWidget(QtCore.Qt.RightDockWidgetArea, dock)
        self.tab = tw
