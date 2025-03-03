from PyQt6.QtWidgets import QFrame, QGridLayout, QLabel
from utils import spacer
from widgets.push_button import PushButton


class ButtonWidget(QFrame):
    """
    A container class of widgets that represents a clickable action with a label.
    This class holds a QLabel and QPushButton.
    """

    def __init__(self, label_title, button_title, tooltip, end=":"):
        super().__init__()

        label = QLabel(self)
        label.setText(label_title + end)
        label.setToolTip(tooltip)
        self.button = PushButton(button_title)
        self.button.setFixedWidth(120)

        self.layout = QGridLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.addWidget(label, 0, 0, 1, 1)
        self.layout.addItem(spacer(), 0, 1, 1, 1)
        self.layout.addWidget(self.button, 0, 2, 1, 1)
        self.setLayout(self.layout)
