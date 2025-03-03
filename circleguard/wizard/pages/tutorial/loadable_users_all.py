from wizard.components.label import WizardLabel
from wizard.components.page import WizardPage
from PyQt6.QtWidgets import QVBoxLayout, QLabel
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import Qt
from utils import resource_path


class TutorialPageLoadableUsersAll(WizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("All Map Replays by User")
        label = WizardLabel(
            "<p>This Loadable represents all the replays by a User on a Map, not just their top score on the map.</p>"
        )
        image = QLabel()
        image.setPixmap(
            QPixmap(resource_path("wizard/mapuser_empty.png")).scaledToWidth(
                500, Qt.TransformationMode.SmoothTransformation
            )
        )
        label2 = WizardLabel(
            '<p>All fields work the same as the previous loadables. "all" in Span is a shorthand way to say you want '
            "all possible replays available from the api by this user on this map. It can also be used in the Span of a Map and User, "
            "and is equivalent to a span of 1-100 in both of those Loadables.</p>"
            "<p>This loadable is useful for checking if someone is remodding their replays. To check for remodding, create this Loadable "
            "with the user and map you suspect them of remodding on, and investigate for Similarity.</p>"
            "<p>It is also useful for checking multiple of a user's replays, not just their top one, on a map (if more than one is "
            "available).</p>"
        )

        layout = QVBoxLayout()
        layout.addWidget(label)
        layout.addWidget(image)
        layout.addWidget(label2)
        self.setLayout(layout)
