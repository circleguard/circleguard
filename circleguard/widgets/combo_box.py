from PyQt6.QtWidgets import QComboBox
from PyQt6.QtGui import QCursor
from PyQt6.QtCore import Qt


# TODO set pointer cursor on combobox popup list as well, I tried
# https://stackoverflow.com/a/44525625/12164878 but couldn't get it to work
class ComboBox(QComboBox):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        # remove WheelFocus from the combobox's focus policy
        # https://stackoverflow.com/a/19382766/12164878
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def wheelEvent(self, event):
        # we never want wheel events to scroll the combobox
        event.ignore()
