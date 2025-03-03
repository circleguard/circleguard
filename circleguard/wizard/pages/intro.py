from wizard.label import WizardLabel
from wizard.page import WizardPage
from PyQt6.QtWidgets import QVBoxLayout


class IntroPage(WizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("Introduction")
        label = WizardLabel(
            "<p>Circleguard is a tool to help you analyze "
            "replays. Either your own, or replays from someone you suspect is cheating.</p>"
            "<p>Circleguard is developed by:"
            "<ul>"
            '<li><a href="https://github.com/tybug">tybug</a></li>'
            "</ul></p>"
            "<p>With contributions from:"
            "<ul>"
            "<li>samuelhklumpers </li>"
            "<li>InvisibleSymbol </li>"
            "<li>sometimes</li>"
            "</ul></p>"
            "<p><b>In the next few pages you will set up circleguard and learn how to use it. Skip at your own risk!</b></p>"
            '<p>If at any point you want to replay this introduction, go to the settings tab and click "Read Tutorial" '
            "under the Dev section."
        )
        layout = QVBoxLayout()
        layout.addWidget(label)
        self.setLayout(layout)
