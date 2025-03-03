from PyQt6.QtWidgets import QLineEdit
from widgets.line_edit import LineEdit


class PasswordEdit(LineEdit):
    """
    A LineEdit that makes the to show/hide the
    password on focus.
    """

    def __init__(self, parent):
        super().__init__(parent)
        self.setEchoMode(QLineEdit.EchoMode.Password)

    def focusInEvent(self, event):
        self.setEchoMode(QLineEdit.EchoMode.Normal)
        return super().focusInEvent(event)

    def focusOutEvent(self, event):
        self.setEchoMode(QLineEdit.EchoMode.Password)
        return super().focusOutEvent(event)
