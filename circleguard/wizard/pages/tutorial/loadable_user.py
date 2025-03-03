from wizard.components.label import WizardLabel
from wizard.components.page import WizardPage
from PyQt6.QtWidgets import QVBoxLayout, QLabel
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import Qt
from utils import resource_path


class TutorialPageLoadableUser(WizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("User")
        label = WizardLabel(
            "<p>A User represents one or more of a User's top plays.</p>"
        )
        image = QLabel()
        image.setPixmap(
            QPixmap(resource_path("wizard/user_empty.png")).scaledToWidth(
                500, Qt.TransformationMode.SmoothTransformation
            )
        )
        label2 = WizardLabel(
            "<p>All fields work the same as the previous Loadables. "
            "If you wanted Cookiezi's top 50 replays, you would enter 124493 as the User id and 1-50 as the Span. "
            "If you wanted his top 20 DT replays, you would enter DT in Mods and 1-20 in Span.</p>"
        )

        layout = QVBoxLayout()
        layout.addWidget(label)
        layout.addWidget(image)
        layout.addWidget(label2)
        self.setLayout(layout)
