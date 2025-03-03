from PyQt6.QtWidgets import QFrame, QGridLayout, QLabel
from PyQt6.QtCore import Qt
from widgets.qh_line import QHLine


class Separator(QFrame):
    """
    Creates a horizontal line with text in the middle.
    Useful to vertically separate other widgets.
    """

    def __init__(self, title):
        super().__init__()

        label = QLabel(self)
        label.setText(title)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.layout = QGridLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.addWidget(QHLine(), 0, 0, 1, 2)
        self.layout.addWidget(label, 0, 2, 1, 1)
        self.layout.addWidget(QHLine(), 0, 3, 1, 2)
        self.setLayout(self.layout)
