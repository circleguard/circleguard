from wizard.label import WizardLabel
from wizard.page import WizardPage
from PyQt6.QtWidgets import QVBoxLayout, QLabel
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import Qt
from utils import resource_path


class TutorialPageChecks(WizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("Investigation")
        label = WizardLabel(
            "<p>Now that you can represent Replays with Loadables, you can start investigating them. "
            "Once you have added the Loadables you want to investigate, check the checkboxes at the top that "
            "you want to investigate them for.</p>"
        )
        image = QLabel()
        image.setPixmap(
            QPixmap(resource_path("wizard/investigation_checkboxes.png")).scaledToWidth(
                650, Qt.TransformationMode.SmoothTransformation
            )
        )
        label2 = WizardLabel(
            "<p>For instance, if you think someone is timewarping, you might add a User loadable for them and "
            "check the Frametime checkbox (as seen above), and then hit Run.</p>"
        )

        layout = QVBoxLayout()
        layout.addWidget(label)
        layout.addWidget(image)
        layout.addWidget(label2)
        self.setLayout(layout)
