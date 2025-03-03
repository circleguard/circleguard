from PyQt6.QtWidgets import QCheckBox
from PyQt6.QtGui import QCursor
from PyQt6.QtCore import Qt


class CheckBox(QCheckBox):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
