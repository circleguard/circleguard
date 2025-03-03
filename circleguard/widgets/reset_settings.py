from PyQt6.QtWidgets import QFrame, QGridLayout, QLabel, QMessageBox
from PyQt6.QtCore import QCoreApplication
from settings import reset_defaults
from utils import spacer
from widgets.push_button import PushButton


class ResetSettings(QFrame):
    def __init__(self):
        super().__init__()
        self.label = QLabel(self)
        self.label.setText("Reset settings:")

        self.button = PushButton(self)
        self.button.setText("Reset")
        self.button.clicked.connect(self.reset_settings)
        self.button.setFixedWidth(120)

        self.layout = QGridLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.addWidget(self.label, 0, 0, 1, 1)
        self.layout.addItem(spacer(), 0, 1, 1, 1)
        self.layout.addWidget(self.button, 0, 2, 1, 1)
        self.setLayout(self.layout)

    def reset_settings(self):
        prompt = QMessageBox.question(
            self,
            "Reset settings",
            "Are you sure?\n"
            "This will reset all settings to their default value, "
            "and the application will quit.",
            buttons=(QMessageBox.StandardButton.No | QMessageBox.StandardButton.Yes),
            defaultButton=QMessageBox.StandardButton.No,
        )
        if prompt == QMessageBox.StandardButton.Yes:
            reset_defaults()
            QCoreApplication.quit()
