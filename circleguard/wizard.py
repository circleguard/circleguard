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
        self.addPage(TutorialPage1())
        self.addPage(TutorialPage2())
        self.addPage(TutorialPage3())
        self.addPage(ConclusionPage())

        # disable help button
        self.setWindowFlags(self.windowFlags() | Qt.CustomizeWindowHint)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.setButtonText(QWizard.CancelButton, "Skip")
        self.setWizardStyle(QWizard.ModernStyle)

        self.setFixedSize(525, 400)

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
        self.darkmode.box.setChecked(get_setting("dark_theme"))

        cache_label = QLabel("Caching reduces downloading time by storing replays when they are first downloaded")
        cache_label.setWordWrap(True)

        self.caching = OptionWidget("Caching", "")
        self.caching.box.setChecked(get_setting("caching"))
        # TODO still won't update the settings checkbox because the main window
        # is loaded before the wizard finishes, so it uses an old setting.
        self.caching.box.stateChanged.connect(partial(update_default, "caching"))

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
                      "<p>Your api key will be stored locally, and is never sent anywhere but osu! servers.</p>"
                      "<p>If you skip this step, you will not be able to run any of the checks.</p>")

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


class TutorialPage1(WizardPage):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle("A Small Tutorial")
        label = QLabel("<p>If you're an experienced reporter, you can skip this page."
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

class TutorialPage2(WizardPage):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle("A Small Tutorial (cont.)")
        label = QLabel("<p>When you run a check on a map, user, osr files, etc. the results can "
                       "be confusing to read at first.</p>"
                       "<p>Circleguard compares replays in sets of two at a time. The similarity "
                       "reported to you is, roughly speaking, the average pixel distance between the two cursors. "
                       "Anything below 18 similarity is almost certainly a replay steal, and when a replay that scores "
                       "below 18 is found, circleguard will audially and visually alert you (OS specific), as well as "
                       "printing to the center area. This threshold is adjustable in the settings and on each tab.</p>"
                       "<p>Circleguard will also print results (but not otherwise alert you) for replays that have a "
                       "similarity under 25 by default. This is to give you suspicious replays that you may want to investiage further. "
                       "This threshold is, of course, adjustable in the settings.")

        label.setTextFormat(Qt.RichText)
        label.setTextInteractionFlags(Qt.TextBrowserInteraction)
        label.setOpenExternalLinks(True)
        label.setWordWrap(True)

        layout = QVBoxLayout()
        layout.addWidget(label)
        self.setLayout(layout)


class TutorialPage3(WizardPage):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle("A Small Tutorial (cont.)")
        label = QLabel("<p>Circleguard tries to present the information to you in a manageble manner, "
                       "but you can change what text is shown.</p>"
                       "<p>In the settings tab, there are multiple "
                       "settings for strings that are shown at different points in the program - when you "
                       "find a cheater, when you finish a comparison, when you find a replay with a low similarity, "
                       "but not quite a cheater (under 25 by default), etc. You can change them to print anything you want, "
                       "such as a different timestamp format, or including the mods each player used. The "
                       "formatting is done through python's <a href=\"https://pyformat.info\">'new-style' strformat</a>.</p>")

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
                       "<li><a href=\"http://reddit.com/r/osureport\">report cheaters at r/osureport</a></li>"
                       "</ul>"
                       "<p>Thanks for helping to clean up osu!</p>")

        label.setTextFormat(Qt.RichText)
        label.setTextInteractionFlags(Qt.TextBrowserInteraction)
        label.setOpenExternalLinks(True)
        label.setWordWrap(True)

        layout = QVBoxLayout()
        layout.addWidget(label)
        self.setLayout(layout)
