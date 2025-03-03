from PyQt6.QtWidgets import QFrame, QLabel, QHBoxLayout
from PyQt6.QtGui import QCursor
from PyQt6.QtCore import Qt
from widgets.check_box import CheckBox


class LabeledCheckbox(QFrame):
    def __init__(self, label):
        super().__init__()
        label = QLabel(label)
        self.checkbox = CheckBox(self)

        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.checkbox)
        layout.addWidget(label)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setLayout(layout)

    def checked(self):
        return self.checkbox.isChecked()

    # toggle checkbox if we're clicked anywhere, so the label can be clicked to
    # toggle as well
    def mousePressEvent(self, event):
        self.checkbox.toggle()
