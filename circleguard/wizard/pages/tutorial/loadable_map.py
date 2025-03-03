from wizard.label import WizardLabel
from wizard.page import WizardPage
from PyQt6.QtWidgets import QVBoxLayout, QLabel
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import Qt
from utils import resource_path


class TutorialPageLoadableMap(WizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("Tutorial (Loadables - Map)")
        label = WizardLabel(
            "<p>A Map represents one or more replays on a map's leaderboard.</p>"
        )
        image = QLabel()
        image.setPixmap(
            QPixmap(resource_path("wizard/map_empty.png")).scaledToWidth(
                500, Qt.TransformationMode.SmoothTransformation
            )
        )
        label2 = WizardLabel(
            '<p>If you wanted the top 50 replays on <a href="https://osu.ppy.sh/beatmapsets/79498#osu/221777">'
            "https://osu.ppy.sh/beatmapsets/79498#osu/221777</a>, you would enter 221777 as the Map id and 1-50 "
            "as the Span (which happens to be the default).</p>"
            '<p>The "Span" field lets you specify which replays on the map\'s leaderboard to represent. For instance, if '
            "you wanted the first, tenth, 12th, and 14th through 20th replays on the leaderboard (for whatever reason), your span would "
            'be "1,10,12,14-20".</p>'
            "<p>As another example, if you've already checked 25 replays of a map, you may only want to represent the "
            "26-50th replays to avoid loading the first 25 replays again. In this case, your span would be 26-50.</p>"
            "<p>Note that although the default span for a Map is 1-50, the osu! api supports loading the top 100 replays of "
            "any map, so you can input a span of 1-100 if you want to check the top 100 replays of a map.</p>"
            "Mods work similarly to a Map Replay. By default (if left empty), a Map will represent the top replays based on score. "
            "If passed, the Map will represent the top replays of the mod. A Span of 1-25 and a Mods of HDDT represents the top 25 "
            "HDDT scores on the map."
        )

        layout = QVBoxLayout()
        layout.addWidget(label)
        layout.addWidget(image)
        layout.addWidget(label2)
        self.setLayout(layout)
