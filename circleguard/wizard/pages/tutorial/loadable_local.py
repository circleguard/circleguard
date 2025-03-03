from wizard.label import WizardLabel
from wizard.page import WizardPage
from PyQt6.QtWidgets import QVBoxLayout, QLabel
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import Qt
from utils import resource_path


class TutorialPageLoadableLocal(WizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("Local Replay")
        label = WizardLabel(
            "<p>A Local Replay represents a replay stored in a .osr file on your computer.</p>"
        )
        image = QLabel()
        image.setPixmap(
            QPixmap(resource_path("wizard/local_replay_empty.png")).scaledToWidth(
                500, Qt.TransformationMode.SmoothTransformation
            )
        )
        label2 = WizardLabel(
            "<p>You can either select a single .osr, or a directory of .osr files.</p>"
        )

        layout = QVBoxLayout()
        layout.addWidget(label)
        layout.addWidget(image)
        layout.addWidget(label2)
        self.setLayout(layout)
