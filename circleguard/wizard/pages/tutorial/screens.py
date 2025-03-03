from wizard.page import WizardPage
from wizard.label import WizardLabel
from PyQt6.QtWidgets import QVBoxLayout


class TutorialPageScreens(WizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("Screens")
        label = WizardLabel(
            "<p>When you launch Circleguard, you will have the option to choose from the "
            '"Visualization" screen, and the "Investigation" screen.</p>'
            "<p>If you only want to visualize a few replays, you should choose the former screen. If you want to "
            "do a broader and more thorough investigation of a particular map, user, or set of replays, you should "
            "choose the latter screen.</p>"
            '<p>The next pages will cover how to use the "Investigation" screen.</p>'
        )

        layout = QVBoxLayout()
        layout.addWidget(label)
        self.setLayout(layout)
