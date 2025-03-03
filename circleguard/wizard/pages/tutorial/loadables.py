from wizard.components.label import WizardLabel
from wizard.components.page import WizardPage
from PyQt6.QtWidgets import QVBoxLayout, QLabel
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import Qt
from utils import resource_path


class TutorialPageLoadables(WizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("Loadables")
        label = WizardLabel(
            "<p>Circleguard uses five different objects (called Loadables) to represent replays. "
            "They are Map Replay, Local Replay, Map, User, and All User Replays on Map.</p>"
            "<p>A Map Replay represents a replay by a single User on a Map.</p>"
        )
        image = QLabel()
        # SmoothTransformation necessary for half decent image quality
        image.setPixmap(
            QPixmap(resource_path("wizard/map_replay_empty.png")).scaledToWidth(
                500, Qt.TransformationMode.SmoothTransformation
            )
        )
        label2 = WizardLabel(
            "<p>If you wanted cookiezi's replay on Freedom Dive, you would enter 129891 "
            "as the Map id and 124493 as the User id.</p>"
            "<p>By default (when Mods is left empty), the highest scoring replay by that user will be used in a Map Replay. "
            "However, if you specify Mods, the replay with that mod combination will be used instead.</p>"
            "<p>Mods are specified using a string made up of two letter combinations — enter HDHR for Hidden Hardrock, "
            "EZ for Easy, NFDT for Nofail Doubletime, etc. The order of the mods does not matter when entering (HDHR is the same as HRHD).</p>"
        )

        layout = QVBoxLayout()
        layout.addWidget(label)
        layout.addWidget(image)
        layout.addWidget(label2)
        self.setLayout(layout)
