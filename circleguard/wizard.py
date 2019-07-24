from functools import partial

# pylint: disable=no-name-in-module
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QPixmap, QIcon
from PyQt5.QtWidgets import QWizard, QWizardPage, QLabel, QVBoxLayout, QGridLayout
# pylint: enable=no-name-in-module

from settings import get_setting, update_default
from widgets import OptionWidget, InputWidget
from utils import resource_path


class WizardPage(QWizardPage):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSubTitle(" ")
        banner = QPixmap(str(resource_path("resources/banner.png")))
        self.setPixmap(QWizard.BannerPixmap, banner)
        image = QPixmap(str(resource_path("resources/logo.png"))).scaled(QSize(banner.height()*0.85, banner.height()*0.85))
        self.setPixmap(QWizard.LogoPixmap, image)


class WelcomeWindow(QWizard):
    def __init__(self):
        super(WelcomeWindow, self).__init__()
        self.setWindowTitle("Wizard")
        self.setWindowIcon(QIcon(str(resource_path("resources/logo.ico"))))
        self.SetupPage = SetupPage()
        self.addPage(IntroPage())
        self.addPage(self.SetupPage)
        self.addPage(ApiKeyPage())
        self.addPage(BeatmapUserIdPage())
        self.addPage(ConclusionPage())

        # disable help button
        self.setWindowFlags(self.windowFlags() | Qt.CustomizeWindowHint)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.setButtonText(QWizard.CancelButton, "Skip")
        self.setWizardStyle(QWizard.ModernStyle)

    def mousePressEvent(self, event):
        focused = self.focusWidget()
        if focused is not None:
            focused.clearFocus()


class IntroPage(WizardPage):
    def __init__(self, parent=None):
        super(IntroPage, self).__init__(parent)
        self.setTitle("Introduction")
        label = QLabel("<p>Circleguard is an all-in-one tool for catching cheaters. It is actively maintained at "
                       "<a href=\"https://github.com/circleguard/circleguard\">https://github.com/circleguard/circleguard</a>.</p>"
                       "<p>Circleguard is developed by:"
                       "<ul>"
                       "<li> tybug </li>"
                       "<li> InvisibleSymbol </li>"
                       "<li> samuelhklumpers </li>"
                       "</ul></p>"
                       "Thanks to <a href=\"https://accalixgfx.com/index.php\">Accalix</a> for creating our logo.")

        label.setTextFormat(Qt.RichText)
        label.setTextInteractionFlags(Qt.TextBrowserInteraction)
        label.setOpenExternalLinks(True)
        label.setWordWrap(True)

        layout = QVBoxLayout()
        layout.addWidget(label)
        self.setLayout(layout)


class SetupPage(WizardPage):
    def __init__(self, parent=None):
        super(SetupPage, self).__init__(parent)
        self.setTitle("Settings")
        dark_label = QLabel("Choose the look and feel of the application")
        dark_label.setWordWrap(True)

        self.darkmode = OptionWidget("Dark mode", "")
        self.darkmode.box.setCheckState(get_setting("dark_theme"))

        cache_label = QLabel("Caching reduces downloading time by reusing already downloaded replays")
        cache_label.setWordWrap(True)

        self.caching = OptionWidget("Caching", "")
        self.caching.box.setCheckState(get_setting("caching"))

        layout = QVBoxLayout()
        layout.addWidget(dark_label)
        layout.addWidget(self.darkmode)
        layout.addWidget(cache_label)
        layout.addWidget(self.caching)
        self.setLayout(layout)


class ApiKeyPage(WizardPage):
    def __init__(self, parent=None):
        super(ApiKeyPage, self).__init__(parent)
        self.setTitle("API Key")
        label = QLabel(self)
        label.setText("<p>Circleguard needs your api key to make requests and download replays. "
                      "Don't worry, this takes less than a minute to complete. </p>"
                      "<p>Go to <a href=\"https://osu.ppy.sh/p/api\">https://osu.ppy.sh/p/api</a>, enter <b>Circleguard</b> "
                      "as your application name, and <a href=\"https://github.com/circleguard/circleguard\">https://github.com/circleguard/circleguard</a> "
                      "as your application url. Paste the api key you receive into the box below.</p>"
                      "<p>Your api key will be stored locally, and is never sent to anyone.</p>"
                      "<p>You can skip this step, but Circleguard will only be able to process local replay files.</p>")

        label.setTextFormat(Qt.RichText)
        label.setTextInteractionFlags(Qt.TextBrowserInteraction)
        label.setOpenExternalLinks(True)
        label.setWordWrap(True)

        apikey_widget = InputWidget("Api Key", "", type_="normal")
        apikey_widget.field.setText(get_setting("api_key"))
        apikey_widget.field.textChanged.connect(partial(update_default, "api_key"))

        layout = QGridLayout()
        layout.addWidget(label, 0, 0, 1, 1)
        layout.addWidget(apikey_widget, 1, 0, 1, 1)
        self.setLayout(layout)


class BeatmapUserIdPage(WizardPage):
    def __init__(self, parent=None):
        super(BeatmapUserIdPage, self).__init__(parent)
        self.setTitle("Small tutorial")
        label = QLabel("<p>If you're an experienced reporter, you can skip this "
                       "step. If you're not, I hope you appreciate the following brief overview.</p>"
                       "<p>When using Circleguard, you will be asked to enter Beatmap Ids and User Ids. "
                       "To find a User Id, go to their profile page and copy the numbers that appear in the url. "
                       "For instance, cookiezi (<a href=\"https://osu.ppy.sh/users/124493\">https://osu.ppy.sh/users/124493</a>) "
                       "has a User Id of 124493.</p>"
                       "<p>Map Ids are slightly trickier - the url contains two ids. The first is the Beatmapset Id, and "
                       "the second is the Beatmap Id. You want to enter the Beatmap Id to circleguard. "
                       "For instance, <a href=\"https://osu.ppy.sh/beatmapsets/39804#osu/129891\">"
                       "https://osu.ppy.sh/beatmapsets/39804#osu/129891</a> has a Beatmapset Id of 39804 and a Beatmap Id of "
                       "129891. Use the Beatmap Id (129891) to check this map.")

        label.setTextFormat(Qt.RichText)
        label.setTextInteractionFlags(Qt.TextBrowserInteraction)
        label.setOpenExternalLinks(True)
        label.setWordWrap(True)

        layout = QVBoxLayout()
        layout.addWidget(label)
        self.setLayout(layout)


class ConclusionPage(WizardPage):
    def __init__(self, parent=None):
        super(ConclusionPage, self).__init__(parent)
        self.setTitle("<3")
        label = QLabel("<p>If you run into any problems with the gui, have suggestions, or want to contribute, join "
                       " our discord or file an issue on the GitHub! We don't bite, we promise :)</p>"
                       "<ul>"
                       "<li><a href=\"https://discord.gg/e84qxkQ\">Discord</a></li>"
                       "<li><a href=\"https://github.com/circleguard/circleguard\">GitHub</a></li>"
                       "<li><a href=\"http://old.reddit.com/r/osureport\">report cheaters at r/osureport</a></li>"
                       "</ul>"
                       "<p>Thanks for helping to clean up osu!</p>")

        label.setTextFormat(Qt.RichText)
        label.setTextInteractionFlags(Qt.TextBrowserInteraction)
        label.setOpenExternalLinks(True)
        label.setWordWrap(True)

        layout = QVBoxLayout()
        layout.addWidget(label)
        self.setLayout(layout)
