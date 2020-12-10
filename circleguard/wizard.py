from functools import partial

from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QPixmap, QIcon, QFont, QMovie
from PyQt5.QtWidgets import QWizard, QWizardPage, QLabel, QVBoxLayout, QGridLayout

from settings import get_setting, set_setting
from widgets import OptionWidget, LineEditSetting, ComboboxSetting
from utils import resource_path


class WizardPage(QWizardPage):
    def __init__(self):
        super().__init__()
        # "In ClassicStyle and ModernStyle, using subtitles is necessary to make the header appear"
        # https://doc.qt.io/qt-5/qwizardpage.html#subTitle-prop
        self.setSubTitle(" ")
        banner = QPixmap(resource_path("wizard/banner.png"))
        self.setPixmap(QWizard.BannerPixmap, banner)
        image = QPixmap(resource_path("logo/logo.png")).scaled(QSize(banner.height() * 0.85, banner.height() * 0.85), transformMode=Qt.SmoothTransformation)
        self.setPixmap(QWizard.LogoPixmap, image)


class CircleguardWizard(QWizard):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Introduction")
        self.setWindowIcon(QIcon(resource_path("logo/logo.ico")))
        self.addPage(IntroPage())
        self.addPage(ApiKeyPage())
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
        self.setWindowFlags(self.windowFlags() | Qt.CustomizeWindowHint)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.setButtonText(QWizard.CancelButton, "Skip")
        self.setWizardStyle(QWizard.ModernStyle)

        self.setFixedSize(750, 625) # 1.2 aspect ratio, same as gui

    def mousePressEvent(self, event):
        focused = self.focusWidget()
        if focused is not None:
            focused.clearFocus()

# same as ``CircleguardWizard``, but with only the tutorial pages
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
        self.setWindowFlags(self.windowFlags() | Qt.CustomizeWindowHint)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.setButtonText(QWizard.CancelButton, "Skip")
        self.setWizardStyle(QWizard.ModernStyle)

        self.setFixedSize(750, 625) # 1.2 aspect ratio, same as gui

    def mousePressEvent(self, event):
        focused = self.focusWidget()
        if focused is not None:
            focused.clearFocus()


class IntroPage(WizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("Introduction")
        label = WizardLabel("<p>Circleguard is an open-source tool to help you catch cheaters.</p>"
                "<p>Circleguard is developed by:"
                "<ul>"
                "<li><a href=\"https://github.com/tybug\">tybug</a></li>"
                "</ul></p>"
                "<p>With contributions from:"
                "<ul>"
                "<li>samuelhklumpers </li>"
                "<li>InvisibleSymbol </li>"
                "<li>sometimes</li>"
                "</ul></p>"
                "<p><b>In the next few pages you will set up circleguard and learn how to use it. Skip at your own risk!</b></p>"
                "<p>If at any point you want to replay this introduction, go to the settings tab and click \"Read Tutorial\" "
                "under the Dev section.")
        layout = QVBoxLayout()
        layout.addWidget(label)
        self.setLayout(layout)


class ApiKeyPage(WizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("API Key")
        label = WizardLabel("<p>Circleguard needs your api key to make requests and download replays. "
                "<p>If you already have your api key, paste it into the box below. If you don't, go to "
                "<a href=\"https://old.ppy.sh/p/api\">https://old.ppy.sh/p/api</a>, enter <b>Circleguard</b> "
                "as your application name, and <a href=\"https://github.com/circleguard/circleguard\">https://github.com/circleguard/circleguard</a> "
                "as your application url. Paste the api key you receive into the box below.</p>"
                "<p>Your api key will be stored locally, and is never sent anywhere but osu! servers.</p>"
                "<p>If you skip this step, you will not be able to use Circleguard.</p>")

        apikey_widget = LineEditSetting("Api Key", "", "normal", "api_key")

        layout = QGridLayout()
        layout.addWidget(label, 0, 0, 1, 1)
        layout.addWidget(apikey_widget, 1, 0, 1, 1)
        self.setLayout(layout)


class TutorialPageScreens(WizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("Screens")
        label = WizardLabel("<p>When you launch Circleguard, you will have the option to choose from the "
                "\"Visualization\" screen, and the \"Investigation\" screen.</p>"
                "<p>If you only want to visualize a few replays, you should choose the former screen. If you want to "
                "do a borader and more thorough investigation of a particular map, user, or set of replays, you should "
                "choose the latter screen.</p>"
                "<p>The next pages will cover how to use the \"Investigation\" screen.</p>")

        layout = QVBoxLayout()
        layout.addWidget(label)
        self.setLayout(layout)


class TutorialPageIds(WizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("Ids")
        label = WizardLabel("<p>When using Circleguard, you will often need to enter Beatmap ids and User ids. "
                "To find a User id, go to their profile page and copy the numbers that appear in the url. "
                "For instance, cookiezi (<a href=\"https://osu.ppy.sh/users/124493\">https://osu.ppy.sh/users/124493</a>) "
                "has a User id of 124493.</p>"
                "<p>Map urls contain two ids. The first is the Beatmapset id, and "
                "the second is the Beatmap id. You want to use the latter (the Beatmap id). "
                "For instance, <a href=\"https://osu.ppy.sh/beatmapsets/39804#osu/129891\">"
                "https://osu.ppy.sh/beatmapsets/39804#osu/129891</a> has a Beatmapset id of 39804 and a Beatmap id of "
                "129891. Use the Beatmap id (129891) to represent this map.</p>")

        layout = QVBoxLayout()
        layout.addWidget(label)
        self.setLayout(layout)


class TutorialPageLoadables(WizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("Loadables")
        label = WizardLabel("<p>Circleguard uses five different objects (called Loadables) to represent replays. "
                "They are Map Replay, Local Replay, Map, User, and All User Replays on Map.</p>"
                "<p>A Map Replay represents a replay by a single User on a Map.</p>")
        image = QLabel()
        # SmoothTransformation necessary for half decent image quality
        image.setPixmap(QPixmap(resource_path("wizard/map_replay_empty.png")).scaledToWidth(500, Qt.SmoothTransformation))
        label2 = WizardLabel("<p>If you wanted cookiezi's replay on Freedom Dive, you would enter 129891 "
                "as the Map id and 124493 as the User id.</p>"
                "<p>By default (when Mods is left empty), the highest scoring replay by that user will be used in a Map Replay. "
                "However, if you specify Mods, the replay with that mod combination will be used instead.</p>"
                "<p>Mods are specified using a string made up of two letter combinations — enter HDHR for Hidden Hardrock, "
                "EZ for Easy, NFDT for Nofail Doubletime, etc. The order of the mods does not matter when entering (HDHR is the same as HRHD).</p>")

        layout = QVBoxLayout()
        layout.addWidget(label)
        layout.addWidget(image)
        layout.addWidget(label2)
        self.setLayout(layout)


class TutorialPageLoadableLocal(WizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("Local Replay")
        label = WizardLabel("<p>A Local Replay represents a replay stored in a .osr file on your computer.</p>")
        image = QLabel()
        image.setPixmap(QPixmap(resource_path("wizard/local_replay_empty.png")).scaledToWidth(500, Qt.SmoothTransformation))
        label2 = WizardLabel("<p>You can either select a single .osr, or a directory of .osr files.</p>")

        layout = QVBoxLayout()
        layout.addWidget(label)
        layout.addWidget(image)
        layout.addWidget(label2)
        self.setLayout(layout)


class TutorialPageLoadableMap(WizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("Tutorial (Loadables - Map)")
        label = WizardLabel("<p>A Map represents one or more replays on a map's leaderboard.</p>")
        image = QLabel()
        image.setPixmap(QPixmap(resource_path("wizard/map_empty.png")).scaledToWidth(500, Qt.SmoothTransformation))
        label2 = WizardLabel("<p>If you wanted the top 50 replays on <a href=\"https://osu.ppy.sh/beatmapsets/79498#osu/221777\">"
                "https://osu.ppy.sh/beatmapsets/79498#osu/221777</a>, you would enter 221777 as the Map id and 1-50 "
                "as the Span (which happens to be the default).</p>"
                "<p>The \"Span\" field lets you specify which replays on the map's leaderboard to represent. For instance, if "
                "you wanted the first, tenth, 12th, and 14th through 20th replays on the leaderboard (for whatever reason), your span would "
                "be \"1,10,12,14-20\".</p>"
                "<p>As another example, if you've already checked 25 replays of a map, you may only want to represent the "
                "26-50th replays to avoid loading the first 25 replays again. In this case, your span would be 26-50.</p>"
                "<p>Note that although the default span for a Map is 1-50, the osu! api supports loading the top 100 replays of "
                "any map, so you can input a span of 1-100 if you want to check the top 100 replays of a map.</p>"
                "Mods work similarly to a Map Replay. By default (if left empty), a Map will represent the top replays based on score. "
                "If passed, the Map will represent the top replays of the mod. A Span of 1-25 and a Mods of HDDT represents the top 25 "
                "HDDT scores on the map.")

        layout = QVBoxLayout()
        layout.addWidget(label)
        layout.addWidget(image)
        layout.addWidget(label2)
        self.setLayout(layout)


class TutorialPageLoadableUser(WizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("User")
        label = WizardLabel("<p>A User represents one or more of a User's top plays.</p>")
        image = QLabel()
        image.setPixmap(QPixmap(resource_path("wizard/user_empty.png")).scaledToWidth(500, Qt.SmoothTransformation))
        label2 = WizardLabel("<p>All fields work the same as the previous Loadables. "
                "If you wanted Cookiezi's top 50 replays, you would enter 124493 as the User id and 1-50 as the Span. "
                "If you wanted his top 20 DT replays, you would enter DT in Mods and 1-20 in Span.</p>")

        layout = QVBoxLayout()
        layout.addWidget(label)
        layout.addWidget(image)
        layout.addWidget(label2)
        self.setLayout(layout)


class TutorialPageLoadableUsersAll(WizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("All Map Replays by User")
        label = WizardLabel("<p>This Loadable represents all the replays by a User on a Map, not just their top score on the map.</p>")
        image = QLabel()
        image.setPixmap(QPixmap(resource_path("wizard/mapuser_empty.png")).scaledToWidth(500, Qt.SmoothTransformation))
        label2 = WizardLabel("<p>All fields work the same as the previous loadables. \"all\" in Span is a shorthand way to say you want "
                "all possible replays available from the api by this user on this map. It can also be used in the Span of a Map and User, "
                "and is equivalent to a span of 1-100 in both of those Loadables.</p>"
                "<p>This loadable is useful for checking if someone is remodding their replays. To check for remodding, create this Loadable "
                "with the user and map you suspect them of remodding on, and investigate for Similarity.</p>"
                "<p>It is also useful for checking multiple of a user's replays, not just their top one, on a map (if more than one is "
                "available).</p>")

        layout = QVBoxLayout()
        layout.addWidget(label)
        layout.addWidget(image)
        layout.addWidget(label2)
        self.setLayout(layout)


class TutorialPageChecks(WizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("Investigation")
        label = WizardLabel("<p>Now that you can represent Replays with Loadables, you can start investigating them. "
            "Once you have added the Loadables you want to investigate, check the checkboxes at the top that "
            "you want to investigate them for.</p>")
        image = QLabel()
        image.setPixmap(QPixmap(resource_path("wizard/investigation_checkboxes.png")).scaledToWidth(650, Qt.SmoothTransformation))
        label2 = WizardLabel("<p>For instance, if you think someone is timewarping, you might add a User loadable for them and "
                "check the Frametime checkbox (as seen above), and then hit Run.</p>")

        layout = QVBoxLayout()
        layout.addWidget(label)
        layout.addWidget(image)
        layout.addWidget(label2)
        self.setLayout(layout)


class TipsPage(WizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("Misc. Tips")
        label = WizardLabel("<p>You can selectively disable certain loadables to exclude them "
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
            "<p>You can press Ctrl+left or Ctrl+right to navigate to adjacent tabs.</p>")

        layout = QVBoxLayout()
        layout.addWidget(label)
        self.setLayout(layout)


class ConclusionPage(WizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("<3")
        label = WizardLabel("<p>If you run into any problems with circleguard, have suggestions, or want to contribute, join "
                " our discord or file an issue on our github repo! We don't bite, we promise :)</p>"
                "<ul>"
                "<li><a href=\"https://discord.gg/e84qxkQ\">Discord</a></li>"
                "<li><a href=\"https://github.com/circleguard/circleguard\">circleguard repo</a></li>"
                "<li><a href=\"http://reddit.com/r/osureport\">report cheaters at r/osureport</a></li>"
                "</ul>"
                "<p>Thanks for helping to clean up osu!</p>")

        layout = QVBoxLayout()
        layout.addWidget(label)
        self.setLayout(layout)


class WizardLabel(QLabel):
    """
    A label which enables all the clicky links and html goodness we want.
    And word wrap.
    """
    def __init__(self, text):
        super().__init__(text)
        self.setTextFormat(Qt.RichText)
        self.setTextInteractionFlags(Qt.TextBrowserInteraction)
        self.setOpenExternalLinks(True)
        self.setWordWrap(True)
