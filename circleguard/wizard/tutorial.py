from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QWizard

from wizard.pages import TipsPage, ConclusionPage
from wizard.pages.tutorial import (
    TutorialPageIds,
    TutorialPageScreens,
    TutorialPageLoadables,
    TutorialPageLoadableLocal,
    TutorialPageLoadableMap,
    TutorialPageLoadableUser,
    TutorialPageLoadableUsersAll,
    TutorialPageChecks,
)
from utils import resource_path

# same as ``WelcomeWizard``, but with only the tutorial pages
class TutorialWizard(QWizard):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Tutorial")
        self.setWindowIcon(QIcon(resource_path("logo/logo.ico")))
        self.addPage(TutorialPageIds())
        self.addPage(TutorialPageScreens())
        self.addPage(TutorialPageLoadables())
        self.addPage(TutorialPageLoadableLocal())
        self.addPage(TutorialPageLoadableMap())
        self.addPage(TutorialPageLoadableUser())
        self.addPage(TutorialPageLoadableUsersAll())
        self.addPage(TutorialPageChecks())
        self.addPage(TipsPage())
        self.addPage(ConclusionPage())

        # disable help button
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.CustomizeWindowHint)
        self.setWindowFlags(
            self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint
        )
        self.setButtonText(QWizard.WizardButton.CancelButton, "Skip")
        self.setWizardStyle(QWizard.WizardStyle.ModernStyle)

        # I don't know why, but the back button's style is messed up. Reset it
        # to what it's supposed to look like.
        button = self.button(QWizard.WizardButton.BackButton)
        button.setStyleSheet(
            "padding-left: 18px; padding-right: 18px;"
            "padding-top: 3px; padding-bottom: 3px;"
        )

        self.setFixedSize(750, 625)  # 1.2 aspect ratio, same as gui

    def mousePressEvent(self, event):
        focused = self.focusWidget()
        if focused is not None:
            focused.clearFocus()
