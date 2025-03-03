from PyQt6.QtWidgets import QWidget, QGridLayout
from PyQt6.QtCore import Qt


class CenteredWidget(QWidget):
    """
    Turns a widget with a fixed size (for example a QCheckBox) into an flexible one which can be affected by the self.layout.
    """

    def __init__(self, widget):
        super().__init__()
        self.layout = QGridLayout()
        self.layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.setContentsMargins(0, 0, 0, 0)
        self.layout.addWidget(widget)
        self.setLayout(self.layout)
