from typing import Dict
from PyQt5.QtCore import QObject
from .receiver import Receiver

class ReceiversManager(QObject):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._rx: Dict[str, Receiver] = {}

    def add(self, rx: Receiver):
        if rx.name in self._rx:
            raise ValueError(f"Receiver '{rx.name}' already exists")
        self._rx[rx.name] = rx

    def remove(self, name: str):
        rx = self._rx.pop(name, None)
        if rx is not None:
            rx.deleteLater()

    def get(self, name: str) -> Receiver:
        return self._rx.get(name)

    def all(self):
        return list(self._rx.values())
