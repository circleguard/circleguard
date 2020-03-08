from functools import partial

from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QPixmap, QIcon, QFont, QMovie
from PyQt5.QtWidgets import QWizard, QWizardPage, QLabel, QVBoxLayout, QGridLayout

from settings import get_setting, set_setting
from widgets import OptionWidget, LineEditSetting
from utils import resource_path


class WizardPage(QWizardPage):
    def __init__(self):
        super().__init__()
        # "In ClassicStyle and ModernStyle, using subtitles is necessary to make the header appear"
        # https://doc.qt.io/qt-5/qwizardpage.html#subTitle-prop
        self.setSubTitle(" ")
        banner = QPixmap(str(resource_path("resources/banner.png")))
        self.setPixmap(QWizard.BannerPixmap, banner)
        image = QPixmap(str(resource_path("resources/logo.png"))).scaled(QSize(banner.height()*0.85, banner.height()*0.85), transformMode=Qt.SmoothTransformation)
        self.setPixmap(QWizard.LogoPixmap, image)


class CircleguardWizard(QWizard):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Wizard")
        self.setWindowIcon(QIcon(str(resource_path("resources/logo.ico"))))
        self.SetupPage = SetupPage()
        self.addPage(IntroPage())
        self.addPage(self.SetupPage)
        self.addPage(ApiKeyPage())
        self.addPage(TutorialPage1())
        self.addPage(TutorialPage2())
        self.addPage(TutorialPage3())
        self.addPage(TutorialPage4())
        self.addPage(TutorialPage5())
        self.addPage(TutorialPage6())
        self.addPage(TutorialPage7())
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
                "<p>Thanks to <a href=\"https://accalixgfx.com/index.php\">Accalix</a> for creating our logo.<p>")
        layout = QVBoxLayout()
        layout.addWidget(label)
        self.setLayout(layout)


class SetupPage(WizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("Settings")
        dark_label = WizardLabel("The theme of Circleguard.")
        self.darkmode = OptionWidget("Dark mode", "", "dark_theme")

        cache_label = WizardLabel("<br><br>Caching reduces downloading time by storing replays when they are first downloaded. "
                "We recommend you leave this enabled — replays take up little space. The osu! api ratelimit "
                "is also quite strict, only allowing 10 downloads per minute. This means that to download the top 100 replays "
                "of a map, you would have to wait 10 minutes. Caching won't reduce this initial download time, but will prevent "
                "you from ever having to download it again in the future.")
        self.caching = OptionWidget("Caching", "", "caching")

        layout = QVBoxLayout()
        layout.addWidget(dark_label)
        layout.addWidget(self.darkmode)
        layout.addWidget(cache_label)
        layout.addWidget(self.caching)
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
                "<p>If you skip this step, you will not be able to use circleguard.</p>")

        apikey_widget = LineEditSetting("Api Key", "", "normal", "api_key")

        layout = QGridLayout()
        layout.addWidget(label, 0, 0, 1, 1)
        layout.addWidget(apikey_widget, 1, 0, 1, 1)
        self.setLayout(layout)


class TutorialPage1(WizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("Tutorial (ids)")
        label = WizardLabel("<p>What follows is a short tutorial in using Circleguard. Skip at your own risk!</p>"
                "<p>When using Circleguard, you will be asked to enter Beatmap ids and User ids. "
                "To find a User id, go to their profile page and copy the numbers that appear in the url. "
                "For instance, cookiezi (<a href=\"https://osu.ppy.sh/users/124493\">https://osu.ppy.sh/users/124493</a>) "
                "has a User id of 124493.</p>"
                "<p>Map ids are slightly trickier - the url contains two ids. The first is the Beatmapset id, and "
                "the second is the Beatmap id. You want to use the latter (the Beatmap id)"
                "For instance, <a href=\"https://osu.ppy.sh/beatmapsets/39804#osu/129891\">"
                "https://osu.ppy.sh/beatmapsets/39804#osu/129891</a> has a Beatmapset id of 39804 and a Beatmap id of "
                "129891. Use the Beatmap id (129891) to represent this map.")

        layout = QVBoxLayout()
        layout.addWidget(label)
        self.setLayout(layout)

class TutorialPage2(WizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("Tutorial (Loadables)")
        label = WizardLabel("<p>Circleguard uses five different objects (called Loadables) to represent replays. "
                "They are Map Replay, Local Replay, Map, User, and All Map Replays by User.</p>"
                "<p>A Map Replay represents a replay by a single User on a Map.</p>")
        image = QLabel()
        # SmoothTransformation necessary for half decent image quality
        image.setPixmap(QPixmap(str(resource_path("resources/tutorial/map_replay_empty.png"))).scaledToWidth(500, Qt.SmoothTransformation))
        label2 = WizardLabel("<p>If you wanted cookiezi's replay on Freedom Dive, for instance you would enter 129891 "
                " as the Map id and 124493 as the User id.</p>"
                "<p>By default (when Mods is left empty), the highest scoring replay by that user will be used in a Map Replay. "
                "However, if you specify Mods, the replay with that mod combination will be used instead.<p>"
                "Mods are specified using a string made up of two letter combinations — enter HDHR for Hidden Hardrock, "
                "EZ for Easy, NFDT for Nofail Doubletime, etc. The order of the mods does not matter when entering (HDHR is the same as HRHD).<p>")

        layout = QVBoxLayout()
        layout.addWidget(label)
        layout.addWidget(image)
        layout.addWidget(label2)
        self.setLayout(layout)

class TutorialPage3(WizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("Tutorial (Loadables - Local Replay)")
        label = WizardLabel("<p>A Local Replay represents a replay stored in a .osr file on your computer.</p>")
        image = QLabel()
        image.setPixmap(QPixmap(str(resource_path("resources/tutorial/local_replay_empty.png"))).scaledToWidth(500, Qt.SmoothTransformation))
        label2 = WizardLabel("<p>Not much more to say here, just select the location of the .osr file you want to represent.</p>")

        layout = QVBoxLayout()
        layout.addWidget(label)
        layout.addWidget(image)
        layout.addWidget(label2)
        self.setLayout(layout)

class TutorialPage4(WizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("Tutorial (Loadables - Map)")
        label = WizardLabel("<p>A Map represents one or more replays on a map's leaderboard.</p>")
        image = QLabel()
        image.setPixmap(QPixmap(str(resource_path("resources/tutorial/map_empty.png"))).scaledToWidth(500, Qt.SmoothTransformation))
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


class TutorialPage5(WizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("Tutorial (Loadables - User)")
        label = WizardLabel("<p>A User represents one or more of a User's top plays.</p>")
        image = QLabel()
        image.setPixmap(QPixmap(str(resource_path("resources/tutorial/user_empty.png"))).scaledToWidth(500, Qt.SmoothTransformation))
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

class TutorialPage6(WizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("Tutorial (Loadables - All Map Replays by User)")
        label = WizardLabel("<p>This Loadable (with quite an unwieldy name — apologies for that) represents all the replays by a User on a Map.</p>")
        image = QLabel()
        image.setPixmap(QPixmap(str(resource_path("resources/tutorial/mapuser_empty.png"))).scaledToWidth(500, Qt.SmoothTransformation))
        label2 = WizardLabel("<p>Again, all fields work similarly to other Loadables. \"all\" in Span is a shorthand way to say you want "
                "all possible replays available from the api by this user on this map. It can also be used in the Span of a Map and User, "
                "and is equivalent to a span of 1-100 in both of those Loadables.</p>"
                "<p>What is this Loadable good for? Mostly remodding checks. If you want to check if someone's remodding their replays, "
                "you can create this Loadable, add their User id and the Map id you suspect them of remodding on, and check it for Replay Stealing. "
                "You might also want to check multiple of a User's replays, not just his top one, on a map for Relax or Aim Correction.</p>")

        layout = QVBoxLayout()
        layout.addWidget(label)
        layout.addWidget(image)
        layout.addWidget(label2)
        self.setLayout(layout)


class TutorialPage7(WizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("Configuring Settings")
        label = WizardLabel("<p>Many aspects of circleguard are configurable.</p>"
                "<p>Common settings can be accessed through the Settings tab. "
                "All settings are located in a config file, including less common settings or "
                "settings that would take too much space to display in the application. "
                "You can edit these settings by pressing \"Open\" under \"Edit Settings File\". </p>"
                "<p>Settings contained in the config file but not in the settings tab include "
                "the content of the messages printed to the terminal, the contents of templates, "
                "and various file locations. More information can be found in the comments of the config file.</p>")

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
    A label with larger font size for easier reading.
    """
    def __init__(self, text):
        super().__init__(text)
        self.setTextFormat(Qt.RichText)
        self.setTextInteractionFlags(Qt.TextBrowserInteraction)
        self.setOpenExternalLinks(True)
        self.setWordWrap(True)
