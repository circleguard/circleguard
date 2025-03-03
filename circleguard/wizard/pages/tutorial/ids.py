from wizard.label import WizardLabel
from wizard.page import WizardPage
from PyQt6.QtWidgets import QVBoxLayout


class TutorialPageIds(WizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("Ids")
        label = WizardLabel(
            "<p>When using Circleguard, you will often need to enter Beatmap ids and User ids. "
            "To find a User id, go to their profile page and copy the numbers that appear in the url. "
            'For instance, cookiezi (<a href="https://osu.ppy.sh/users/124493">https://osu.ppy.sh/users/124493</a>) '
            "has a User id of 124493.</p>"
            "<p>Map urls contain two ids. The first is the Beatmapset id, and "
            "the second is the Beatmap id. You want to use the latter (the Beatmap id). "
            'For instance, <a href="https://osu.ppy.sh/beatmapsets/39804#osu/129891">'
            "https://osu.ppy.sh/beatmapsets/39804#osu/129891</a> has a Beatmapset id of 39804 and a Beatmap id of "
            "129891. Use the Beatmap id (129891) to represent this map.</p>"
        )

        layout = QVBoxLayout()
        layout.addWidget(label)
        self.setLayout(layout)
