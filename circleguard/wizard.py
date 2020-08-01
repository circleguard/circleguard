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
        self.setWindowTitle("Wizard")
        self.setWindowIcon(QIcon(resource_path("logo/logo.ico")))
        self.addPage(IntroPage())
        self.addPage(ApiKeyPage())
        self.addPage(SettingsSetupPage())
        self.addPage(TutorialPageId())
        self.addPage(TutorialPageLoadables())
        self.addPage(TutorialPageLoadableLocal())
        self.addPage(TutorialPageLoadableMap())
        self.addPage(TutorialPageLoadableUser())
        self.addPage(TutorialPageLoadableUsersAll())
        self.addPage(TutorialPageChecks())
        self.addPage(SettingsPage())
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
        label = WizardLabel("<p>Circleguard is an all-in-one tool for catching cheaters. It is actively maintained at "
                "<a href=\"https://github.com/circleguard/circleguard\">https://github.com/circleguard/circleguard</a>.</p>"
                "<p>We support detecting Replay Stealing, Relax, and Aim Correction.</p>"
                "<p>Circleguard is developed by:"
                "<ul>"
                "<li>tybug </li>"
                "<li>InvisibleSymbol </li>"
                "<li>samuelhklumpers </li>"
                "</ul></p>"
                "<p>Thanks to <a href=\"https://accalixgfx.com/index.php\">Accalix</a> for creating our logo.<p>"
                "<p>If at any point you want to replay this wizard, go to the settings tab and click \"Read Tutorial\" "
                "under the Dev section.")
        layout = QVBoxLayout()
        layout.addWidget(label)
        self.setLayout(layout)


class ApiKeyPage(WizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("API Key")
        label = WizardLabel("<p>Circleguard needs your api key to make requests and download replays. "
                "<p>If you already have your api key, paste it in the box below. If you don't, go to "
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

class SettingsSetupPage(WizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("Settings")
        dark_label = WizardLabel("The theme of Circleguard.")
        self.theme = ComboboxSetting("Theme", "", "theme")

        cache_label = WizardLabel("<br><br>Caching reduces downloading time by storing replays when they are first downloaded. "
                "We recommend you leave this enabled — replays take up little space. The osu! api ratelimit "
                "is also quite strict, only allowing 10 downloads per minute. This means that to download the top 100 replays "
                "of a map, you would have to wait 10 minutes. Caching won't reduce this initial download time, but will prevent "
                "you from ever having to download it again in the future.")
        self.caching = OptionWidget("Caching", "", "caching")

        layout = QVBoxLayout()
        layout.addWidget(dark_label)
        layout.addWidget(self.theme)
        layout.addWidget(cache_label)
        layout.addWidget(self.caching)
        self.setLayout(layout)


class TutorialPageId(WizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("Tutorial (ids)")
        label = WizardLabel("<p>What follows is a short tutorial in using Circleguard. Feel free to try out the examples "
                "yourself in the gui as you work your way through the tutorial. Skip at your own risk!</p>"
                "<p>When using Circleguard, you will be asked to enter Beatmap ids and User ids. "
                "To find a User id, go to their profile page and copy the numbers that appear in the url. "
                "For instance, cookiezi (<a href=\"https://osu.ppy.sh/users/124493\">https://osu.ppy.sh/users/124493</a>) "
                "has a User id of 124493.</p>"
                "<p>Map urls contain two ids. The first is the Beatmapset id, and "
                "the second is the Beatmap id. You want to use the latter (the Beatmap id)"
                "For instance, <a href=\"https://osu.ppy.sh/beatmapsets/39804#osu/129891\">"
                "https://osu.ppy.sh/beatmapsets/39804#osu/129891</a> has a Beatmapset id of 39804 and a Beatmap id of "
                "129891. Use the Beatmap id (129891) to represent this map.")

        layout = QVBoxLayout()
        layout.addWidget(label)
        self.setLayout(layout)


class TutorialPageLoadables(WizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("Tutorial (Loadables)")
        label = WizardLabel("<p>Circleguard uses five different objects (called Loadables) to represent replays. "
                "They can be created on the left half of the Main tab. "
                "They are Map Replay, Local Replay, Map, User, and All Map Replays by User.</p>"
                "<p>A Map Replay represents a replay by a single User on a Map.</p>")
        image = QLabel()
        # SmoothTransformation necessary for half decent image quality
        image.setPixmap(QPixmap(resource_path("wizard/map_replay_empty.png")).scaledToWidth(500, Qt.SmoothTransformation))
        label2 = WizardLabel("<p>If you wanted cookiezi's replay on Freedom Dive, for instance you would enter 129891 "
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
        self.setTitle("Tutorial (Loadables - Local Replay)")
        label = WizardLabel("<p>A Local Replay represents a replay stored in a .osr file on your computer.</p>")
        image = QLabel()
        image.setPixmap(QPixmap(resource_path("wizard/local_replay_empty.png")).scaledToWidth(500, Qt.SmoothTransformation))
        label2 = WizardLabel("<p>Not much more to say here, just select the location of the .osr file you want to represent.</p>")

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
                "<p>The 'Span' argument lets you specify what replays of the map's leaderboard to represent. For instance, if "
                "you wanted the first, tenth, 12th, and 14th through 20th replays on the leaderboard (for whatever reason), your span would "
                "be 1,10,12,14-20.</p>"
                "<p>Another example — if you've already checked 25 replays of a map for cheating, you may only want to represent the "
                "latter half to avoid loading the first 25 replays again. In this case, your span would be 25-50.</p>"
                "<p>Note that although the default span for a Map is 1-50, the osu! api supports loading the top 100 replays of "
                "any map, so you can input a span of 1-100 if you want to check the top 100 replays of a map.</p>"
                "Mods work similarly to a Map Replay — by default (if left empty), a Map will represent the top replays based on score. "
                "If passed, a Map will represent the top replays of the mod — a Span of 1-25 and a Mods of HDDT represents the top 25 "
                "HDDT scores on the map.")

        layout = QVBoxLayout()
        layout.addWidget(label)
        layout.addWidget(image)
        layout.addWidget(label2)
        self.setLayout(layout)


class TutorialPageLoadableUser(WizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("Tutorial (Loadables - User)")
        label = WizardLabel("<p>A User represents one or more of a User's top plays.</p>")
        image = QLabel()
        image.setPixmap(QPixmap(resource_path("wizard/user_empty.png")).scaledToWidth(500, Qt.SmoothTransformation))
        label2 = WizardLabel("<p>All fields work similarly to the other Loadables we've explained. "
                "If you wanted Cookiezi's top 50 replays, you would enter 124493 as the User id and 1-50 as the Span. "
                "If you wanted his top 20 DT replays, you would enter DT in Mods and 1-20 in Span.</p>"
                "<p>Note that if a User has fewer replays available for download than you specify in Span, Circleguard "
                "will supply as many replays as possible, but you may see a number of replays which is lower than you expect. "
                "You haven't done anything wrong if you experience this; just be aware of why it occurs.</p>")

        layout = QVBoxLayout()
        layout.addWidget(label)
        layout.addWidget(image)
        layout.addWidget(label2)
        self.setLayout(layout)


class TutorialPageLoadableUsersAll(WizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("Tutorial (Loadables - All Map Replays by User)")
        label = WizardLabel("<p>This Loadable represents all the replays by a User on a Map, not just their top score.</p>")
        image = QLabel()
        image.setPixmap(QPixmap(resource_path("wizard/mapuser_empty.png")).scaledToWidth(500, Qt.SmoothTransformation))
        label2 = WizardLabel("<p>Again, all fields work similarly to other Loadables. \"all\" in Span is a shorthand way to say you want "
                "all possible replays available from the api by this user on this map. It can also be used in the Span of a Map and User, "
                "and is equivalent to a span of 1-100 in both of those Loadables.</p>"
                "<p>What is this Loadable good for? Mostly remodding checks. If you want to check if someone's remodding their replays, "
                "you can create this Loadable, add their User id and the Map id you suspect them of remodding on, and check it for Replay Stealing. "
                "You might also want to check multiple of a User's replays, not just his top one, on a Map for Relax or Aim Correction.</p>")

        layout = QVBoxLayout()
        layout.addWidget(label)
        layout.addWidget(image)
        layout.addWidget(label2)
        self.setLayout(layout)


class TutorialPageChecks(WizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("Tutorial (Checks)")
        label = WizardLabel("<p>Now that you can represent Replays with Loadables, you can start investigating them for cheats. Circleguard "
                            "supports four different kinds of Checks.</p>")
        image = QLabel()
        image.setPixmap(QPixmap(resource_path("wizard/checks_dropdown.png")).scaledToWidth(500, Qt.SmoothTransformation))
        label2 = WizardLabel("<p>Each of these should be self explanatory. If you want to check a Loadable for a certain cheat, just drag and "
                "drop it onto the appropriate Check, then hit run.</p>"
                "<p>Replay Stealing and Visualize are both different from the others. Replay Stealing has two areas for you to drag Loadables "
                "onto - if only one of them has any Loadables, each replay will be compared against each other replay. eg, if you "
                "give a Map with span=\"1-50\" to one area of a Replay Stealing Check, and nothing to the other area, it will compare "
                "each replay in the top 50 of that map against each other replay in the top 50. However, if you drag a Map Replay to "
                "the other area of the Check, it will compare just the Replay Map against each of the replays in the top 50. This "
                "can be useful if you want to check if a specific user stole from a map, without comparing replays that don't involve "
                "the player you suspect.</p>"
                "<p>A Visualize Check doesn't perform any sort of analysis on the replays, but instead plays back the replays in a new window, "
                "simulating osu! gameplay, including the beatmap. This is useful for manual inspection and frame-by-frame visualization.<p>")

        layout = QVBoxLayout()
        layout.addWidget(label)
        layout.addWidget(image)
        layout.addWidget(label2)
        self.setLayout(layout)


class SettingsPage(WizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("Configuring Settings")
        label = WizardLabel("<p>Thresholds for the different Checks can be changed in the Thresholds tab, and other common settings in "
                "the Settings tab.</p>"
                "<p>The full range of settings (of which there are quite a few — you can customize Circleguard heavily!) "
                "can be accessed by pressing \"Open Settings\" at the top of the Settings tab. Be sure to read the comments in that file "
                "for instructions on editing the settings.</p>")

        layout = QVBoxLayout()
        layout.addWidget(label)
        self.setLayout(layout)


class ConclusionPage(WizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("<3")
        label = WizardLabel("<p>If you run into any problems with the gui, have suggestions, or want to contribute, join "
                " our discord or file an issue on the GitHub! We don't bite, we promise :)</p>"
                "<ul>"
                "<li><a href=\"https://discord.gg/e84qxkQ\">Discord</a></li>"
                "<li><a href=\"https://github.com/circleguard/circleguard\">GitHub</a></li>"
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
