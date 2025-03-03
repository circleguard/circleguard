from wizard.components.page import WizardPage

from wizard.components.label import WizardLabel
from PyQt6.QtWidgets import QVBoxLayout


class TipsPage(WizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("Misc. Tips")
        label = WizardLabel(
            "<p>You can selectively disable certain loadables to exclude them "
            "from the current run but still keep them around for later. This can be done by clicking "
            "the blue check to disable a loadable, and the red X to re-enable it.</p>"
            "<p>You can shift+click the blue check to disable all <em>other</em> loadables, but not the one you clicked. "
            "You can shift+click the red X of any disabled loadable to re-enable <em>all</em> loadables, including the one you clicked.</p>"
            "<p>Each loadable has a shortcut associated with it that will create a new loadable of that type when pressed.</p>"
            "<ul>"
            "<li>Map Replay: <b>R</b></li>"
            "<li>Local Replay: <b>L</b></li>"
            "<li>Map: <b>M</b></li>"
            "<li>User: <b>U</b></li>"
            "<li>All User Replays on Map: <b>A</b></li>"
            "</ul>"
            "<p>You can press Ctrl+left or Ctrl+right to navigate to adjacent tabs.</p>"
        )

        layout = QVBoxLayout()
        layout.addWidget(label)
        self.setLayout(layout)
