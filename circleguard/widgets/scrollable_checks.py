from PyQt6.QtWidgets import QFrame, QVBoxLayout
from PyQt6.QtCore import Qt

class ScrollableChecksWidget(QFrame):
    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout()
        self.layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.setLayout(self.layout)
