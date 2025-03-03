from wizard.components.label import WizardLabel
from wizard.components.page import WizardPage
from PyQt6.QtWidgets import QVBoxLayout


class ConclusionPage(WizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("<3")
        label = WizardLabel(
            "<p>If you run into any problems with circleguard, have suggestions, or want to contribute, join "
            " the discord or file an issue on the github repository! I don't bite, I promise :)</p>"
            "<ul>"
            '<li><a href="https://discord.gg/e84qxkQ">circleguard discord</a></li>'
            '<li><a href="https://github.com/circleguard/circleguard">circleguard repository</a></li>'
            '<li><a href="http://reddit.com/r/osureport">report cheaters at r/osureport</a></li>'
            "</ul>"
            "<p>Thanks for helping to clean up osu!</p>"
        )

        layout = QVBoxLayout()
        layout.addWidget(label)
        self.setLayout(layout)
