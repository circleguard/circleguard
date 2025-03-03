from PyQt6.QtWidgets import QFrame, QGridLayout, QLabel
from PyQt6.QtCore import pyqtSignal
from widgets.push_button import PushButton


class EntryWidget(QFrame):
    """
    Represents a single entry of some kind of data, consisting of a title, a
    button and the data which is stored at self.data.
    When the button is pressed, pressed_signal is emitted with the data.
    """

    pressed_signal = pyqtSignal(object)

    def __init__(self, title, action_name, data):
        super().__init__()
        self.data = data
        self.button = PushButton(action_name)
        self.button.setFixedWidth(100)
        self.button.clicked.connect(self.button_pressed)
        self.layout = QGridLayout()
        self.layout.addWidget(QLabel(title), 0, 0, 1, 1)
        self.layout.addWidget(self.button, 0, 1, 1, 1)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.layout)

    def button_pressed(self, _):
        self.pressed_signal.emit(self.data)
