from PyQt6.QtGui import QRegularExpressionValidator
from PyQt6.QtCore import QRegularExpression
from widgets.line_edit import LineEdit


class IDLineEdit(LineEdit):
    r"""
    A LineEdit that does not allow anything but digits to be entered.

    Notes
    -----
    Specifically, anything not matched by the regex ``\d*`` is not registered.
    """

    def __init__(self, parent):
        super().__init__(parent)
        validator = QRegularExpressionValidator(QRegularExpression(r"\d*"))
        self.setValidator(validator)
