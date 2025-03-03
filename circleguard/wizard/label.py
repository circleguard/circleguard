from PyQt6.QtWidgets import QLabel
from PyQt6.QtCore import Qt


class WizardLabel(QLabel):
    """
    A label which enables all the clicky links and html goodness we want.
    And word wrap.
    """

    def __init__(self, text):
        super().__init__(text)
        self.setTextFormat(Qt.TextFormat.RichText)
        self.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
        self.setOpenExternalLinks(True)
        self.setWordWrap(True)
