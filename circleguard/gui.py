import os
from pathlib import Path
from multiprocessing.pool import ThreadPool
from queue import Queue, Empty
from functools import partial
import logging
import colorsys
from datetime import datetime
# pylint: disable=no-name-in-module
from PyQt5.QtCore import Qt, QTimer, qInstallMessageHandler, QObject, pyqtSignal
from PyQt5.QtWidgets import (QWidget, QTabWidget, QTextEdit, QPushButton, QLabel, QScrollArea, QFrame, QProgressBar,
                             QVBoxLayout, QShortcut, QGridLayout, QApplication, QMainWindow, QSizePolicy)
from PyQt5.QtGui import QPalette, QColor, QIcon, QKeySequence, QTextCursor, QPainter
# pylint: enable=no-name-in-module

from circleguard import Circleguard, set_options, loader
from circleguard import __version__ as cg_version
from visualizer import VisualizerWindow
from utils import resource_path
from widgets import (Threshold, set_event_window, InputWidget, ResetSettings, WidgetCombiner,
                     FolderChooser, IdWidgetCombined, Separator, OptionWidget, ButtonWidget,
                     CompareTopPlays, CompareTopUsers, ThresholdCombined, LoglevelWidget,
                     TopPlays, BeatmapTest, StringFormatWidget, ComparisonResult)

from settings import get_setting, update_default
import wizard

__version__ = "1.0.0"

log = logging.getLogger(__name__)


# logging methodology heavily adapted from https://stackoverflow.com/questions/28655198/best-way-to-display-logs-in-pyqt
class Handler(QObject, logging.Handler):
    new_message = pyqtSignal(object)

    def __init__(self):
        super().__init__()

    def emit(self, record):
        message = self.format(record)
        self.new_message.emit(message)


class WindowWrapper(QMainWindow):
    def __init__(self):
        super(WindowWrapper, self).__init__()
        self.progressbar = QProgressBar()
        self.progressbar.setFixedWidth(250)
        self.current_state_label = QLabel("Idle")
        # statusBar() is a qt function that will create a status bar tied to the window
        # if it doesnt exist, and access the existing one if it does.
        self.statusBar().addWidget(WidgetCombiner(self.progressbar, self.current_state_label))
        self.statusBar().setSizeGripEnabled(False)
        self.statusBar().setContentsMargins(8, 2, 10, 3)

        self.main_window = MainWindow()
        self.main_window.main_tab.reset_progressbar_signal.connect(self.reset_progressbar)
        self.main_window.main_tab.increment_progressbar_signal.connect(self.increment_progressbar)
        self.main_window.main_tab.update_label_signal.connect(self.update_label)
        self.main_window.main_tab.add_comparison_result_signal.connect(self.add_comparison_result)
        self.main_window.main_tab.write_to_terminal_signal.connect(self.main_window.main_tab.write)

        self.setCentralWidget(self.main_window)
        QShortcut(QKeySequence(Qt.CTRL+Qt.Key_Right), self, self.tab_right)
        QShortcut(QKeySequence(Qt.CTRL+Qt.Key_Left), self, self.tab_left)

        self.setWindowTitle(f"Circleguard (Backend v{cg_version} / Frontend v{__version__})")
        self.setWindowIcon(QIcon(str(resource_path("resources/logo.ico"))))
        self.start_timer()
        self.debug_window = None

        handler = Handler()
        logging.getLogger("circleguard").addHandler(handler)
        logging.getLogger(__name__).addHandler(handler)
        formatter = logging.Formatter("[%(levelname)s] %(asctime)s  %(message)s ", datefmt="%Y/%m/%d %I:%M:%S %p")
        handler.setFormatter(formatter)
        handler.new_message.connect(self.print_debug)

    # I know, I know...we have a stupid amount of layers.
    # WindowWrapper -> MainWindow -> MainTab -> Tabs
    def tab_right(self):
        tabs = self.main_window.main_tab.tabs
        tabs.setCurrentIndex(tabs.currentIndex() + 1)

    def tab_left(self):
        tabs = self.main_window.main_tab.tabs
        tabs.setCurrentIndex(tabs.currentIndex() - 1)

    def mousePressEvent(self, event):
        focused = self.focusWidget()
        if focused is not None:
            focused.clearFocus()
        super(WindowWrapper, self).mousePressEvent(event)

    def start_timer(self):
        timer = QTimer(self)
        timer.timeout.connect(self.run_timer)
        timer.start(250)

    def run_timer(self):
        """
        check for stderr messages (because logging prints to stderr not stdout, and
        it's nice to have stdout reserved) and then print cg results
        """
        self.main_window.main_tab.print_results()

    def print_debug(self, message):
        """
        Message is the string message sent to the io stream
        """
        if get_setting("log_save"):
            if not os.path.exists(get_setting('log_dir')):  # create dir if nonexistent
                os.makedirs(get_setting('log_dir'))
            directory = os.path.join(get_setting("log_dir"), "circleguard.log")
            with open(directory, 'a+') as f:  # append so it creates a file if it doesn't exist
                f.seek(0)
                data = f.read().splitlines(True)
            data.append(message+"\n")
            with open(directory, 'w+') as f:
                f.writelines(data[-10000:])  # keep file at 10000 lines

        if get_setting("log_output") == 0:
            pass

        if get_setting("log_output") == 1 or get_setting("log_output") == 3:
            self.main_window.main_tab.write(message)

        if get_setting("log_output") == 2 or get_setting("log_output") == 3:
            if self.debug_window and self.debug_window.isVisible():
                self.debug_window.write(message)
            else:
                self.debug_window = DebugWindow()
                self.debug_window.show()
                self.debug_window.write(message)

    def update_label(self, text):
        self.current_state_label.setText(text)

    def increment_progressbar(self, increment):
        self.progressbar.setValue(self.progressbar.value() + increment)

    def reset_progressbar(self, max_value):
        if not max_value == -1:
            self.progressbar.setValue(0)
            self.progressbar.setRange(0, max_value)
        else:
            self.progressbar.setRange(0, 100)
            self.progressbar.reset()

    def add_comparison_result(self, result):
        # this right here could very well lead to some memory issues. I tried to avoid
        # leaving a reference to the replays in this method, but it's quite possible
        # things are still not very clean. Ideally only ComparisonResult would have a
        # reference to the two replays, and result should have no references left.
        r1 = result.replay1
        r2 = result.replay2
        timestamp = datetime.now()
        text = get_setting("string_result_text").format(ts=timestamp, similarity=result.similarity,
                                                        replay1_name=r1.username, replay2_name=r2.username,
                                                        later_name=result.later_name)
        result_widget = ComparisonResult(text, r1, r2)
        result_widget.button.clicked.connect(partial(self.main_window.main_tab.visualize, result_widget.replay1, result_widget.replay2))
        # remove info text if shown
        if not self.main_window.results_tab.results.info_label.isHidden():
            self.main_window.results_tab.results.info_label.hide()
        self.main_window.results_tab.results.layout.addWidget(result_widget)


class DebugWindow(QMainWindow):
    def __init__(self):
        super(DebugWindow, self).__init__()
        terminal = QTextEdit()
        terminal.setReadOnly(True)
        terminal.ensureCursorVisible()
        self.terminal = terminal
        self.setCentralWidget(self.terminal)
        self.setFixedSize(800, 350)

    def write(self, message):
        self.terminal.append(message)
        self.scroll_to_bottom()

    def scroll_to_bottom(self):
        cursor = QTextCursor(self.terminal.document())
        cursor.movePosition(QTextCursor.End)
        self.terminal.setTextCursor(cursor)


class MainWindow(QWidget):
    def __init__(self):
        super(MainWindow, self).__init__()

        self.tab_widget = QTabWidget()
        self.main_tab = MainTab()
        self.results_tab = ResultsTab()
        self.settings_tab = SettingsTab()
        self.tab_widget.addTab(self.main_tab, "Main Tab")
        self.tab_widget.addTab(self.results_tab, "Results Tab")
        self.tab_widget.addTab(self.settings_tab, "Settings Tab")
        # so when we switch from settings tab to main tab, whatever tab we're on gets changed if we delete our api key
        self.tab_widget.currentChanged.connect(self.main_tab.switch_run_button)

        self.main_layout = QVBoxLayout()
        self.main_layout.addWidget(self.tab_widget)
        self.main_layout.setContentsMargins(10, 10, 10, 0)
        self.setLayout(self.main_layout)


class MainTab(QWidget):
    reset_progressbar_signal = pyqtSignal(int)  # max progress
    increment_progressbar_signal = pyqtSignal(int)  # increment value
    update_label_signal = pyqtSignal(str)
    write_to_terminal_signal = pyqtSignal(str)
    add_comparison_result_signal = pyqtSignal(object)  # Result

    TAB_REGISTER = [
        {"name": "MAP",    "requires_api": True},
        {"name": "SCREEN", "requires_api": True},
        {"name": "LOCAL",  "requires_api": False},
        {"name": "VERIFY", "requires_api": True},
    ]

    def __init__(self):
        super(MainTab, self).__init__()
        self.q = Queue()
        self.cg_running = False
        tabs = QTabWidget()
        self.map_tab = MapTab()
        self.user_tab = UserTab()
        self.local_tab = LocalTab()
        self.verify_tab = VerifyTab()
        tabs.addTab(self.map_tab, "Check Map")
        tabs.addTab(self.user_tab, "Screen User")
        tabs.addTab(self.local_tab, "Check Local Replays")
        tabs.addTab(self.verify_tab, "Verify")
        self.tabs = tabs
        self.tabs.currentChanged.connect(self.switch_run_button)

        terminal = QTextEdit()
        terminal.setFocusPolicy(Qt.ClickFocus)
        terminal.setReadOnly(True)
        terminal.ensureCursorVisible()
        self.terminal = terminal

        self.run_button = QPushButton()
        self.run_button.setText("Run")
        self.run_button.clicked.connect(self.run)

        layout = QVBoxLayout()
        layout.addWidget(tabs)
        layout.addWidget(self.terminal)
        layout.addWidget(self.run_button)
        self.setLayout(layout)
        self.run_type = "NONE"  # set after you click run, depending on your current tab
        self.switch_run_button()  # disable run button if there is no api key

    def write(self, message):
        self.terminal.append(str(message).strip())
        self.scroll_to_bottom()

    def scroll_to_bottom(self):
        cursor = QTextCursor(self.terminal.document())
        cursor.movePosition(QTextCursor.End)
        self.terminal.setTextCursor(cursor)

    def run(self):
        current_tab = self.tabs.currentIndex()
        self.run_type = MainTab.TAB_REGISTER[current_tab]["name"]
        pool = ThreadPool(processes=1)
        pool.apply_async(self.run_circleguard)

    def switch_run_button(self):
        if not self.cg_running:
            self.run_button.setEnabled(not MainTab.TAB_REGISTER[self.tabs.currentIndex()]["requires_api"] if get_setting("api_key") == "" else True)
        else:
            # this line causes a "QObject::startTimer: Timers cannot be started from another thread" print
            # statement even though no timer interaction is going on; not sure why it happens but it doesn't
            # impact functionality. Still might be worth looking into
            self.run_button.setEnabled(False)

    def run_circleguard(self):
        self.cg_running = True
        self.switch_run_button()
        self.update_label_signal.emit("Loading Replays")
        try:
            set_options(cache=bool(get_setting("caching")))
            cg = Circleguard(get_setting("api_key"), resource_path(os.path.join(get_setting("cache_dir"), "cache.db")))
            if self.run_type == "MAP":
                tab = self.map_tab
                # TODO: generic failure terminal print method, 'please enter a map id' or 'that map has no leaderboard scores, please double check the id'
                #       maybe fancy flashing red stars for required fields
                map_id_str = tab.id_combined.map_id.field.text()
                map_id = int(map_id_str) if map_id_str != "" else 0

                user_id_str = tab.id_combined.user_id.field.text()
                user_id = int(user_id_str) if user_id_str != "" else None
                
                num = tab.compare_top.slider.value()
                thresh = tab.threshold.slider.value()
                check = cg.create_map_check(map_id, u=user_id, num=num, thresh=thresh)

            if self.run_type == "SCREEN":
                tab = self.user_tab
                user_id_str = tab.user_id.field.text()
                user_id = int(user_id_str) if user_id_str != "" else 0
                num_top = tab.compare_top_map.slider.value()
                num_users = tab.compare_top_users.slider.value()
                thresh = tab.threshold.slider.value()
                check = cg.create_user_check(user_id, num_top, num_users, thresh=thresh)

            if self.run_type == "LOCAL":
                tab = self.local_tab
                path = Path(tab.folder_chooser.path)
                thresh = tab.threshold.slider.value()
                check = cg.create_local_check(path, thresh=thresh)

            if self.run_type == "VERIFY":
                tab = self.verify_tab
                map_id_str = tab.map_id.field.text()
                map_id = int(map_id_str) if map_id_str != "" else 0
                user_id_1_str = tab.user_id_1.field.text()
                user_id_1 = int(user_id_1_str) if user_id_1_str != "" else 0
                user_id_2_str = tab.user_id_2.field.text()
                user_id_2 = int(user_id_2_str) if user_id_2_str != "" else 0
                thresh = tab.threshold.slider.value()
                check = cg.create_verify_check(map_id, user_id_1, user_id_2, thresh=thresh)

            # user_check convenience method comes with some caveats; a list
            # of list of check objects is returned instead of a singl Check
            # because it checks for remodding and replay stealing for
            # each top play of the user
            if self.run_type == "SCREEN":
                num_to_load = 0
                for check_list in check:
                    for check_ in check_list:
                        num_to_load += len(check_.all_replays())
            else:
                num_to_load = len(check.all_replays())
            self.reset_progressbar_signal.emit(num_to_load)
            cg.loader.new_session(num_to_load)
            timestamp = datetime.now()
            self.write_to_terminal_signal.emit(get_setting("message_loading_replays").format(ts=timestamp, num_replays=num_to_load))
            if self.run_type == "SCREEN":
                for check_list in check:
                    for check_ in check_list:
                        for replay in check_.all_replays():
                            cg.load(check_, replay)
                        check_.loaded = True
            else:
                for replay in check.all_replays():
                    cg.load(check, replay)
                    self.increment_progressbar_signal.emit(1)
                check.loaded = True


            self.reset_progressbar_signal.emit(0)  # changes progressbar into a "progressing" state
            timestamp = datetime.now()
            self.write_to_terminal_signal.emit(get_setting("message_starting_comparing").format(ts=timestamp, num_replays=num_to_load))
            if self.run_type == "SCREEN":
                for check_list in check:
                    for check_ in check_list:
                        for result in cg.run(check_):
                            self.q.put(result)
            else:
                for result in cg.run(check):
                    self.q.put(result)
            self.reset_progressbar_signal.emit(-1)  # resets progressbar so it's empty again

            timestamp = datetime.now()
            self.write_to_terminal_signal.emit(get_setting("message_finished_comparing").format(ts=timestamp, num_replays=num_to_load))

        except Exception:
            log.exception("Error while running circlecore. Please "
                          "report this to the developers through discord or github.\n")

        self.cg_running = False
        self.update_label_signal.emit("Idle")
        self.switch_run_button()

    def print_results(self):
        try:
            while True:
                result = self.q.get(block=False)
                # self.visualize(result.replay1, result.replay2)
                if result.ischeat:
                    timestamp = datetime.now()
                    r1 = result.replay1
                    r2 = result.replay2
                    msg = get_setting("message_cheater_found").format(ts=timestamp, similarity=result.similarity,
                                                                      replay1_name=r1.username, replay2_name=r2.username,
                                                                      later_name=result.later_name, replay1_mods=r1.mods,
                                                                      replay2_mods=r2.mods, replay1_id=r1.replay_id,
                                                                      replay2_id=r2.replay_id)
                    self.write(msg)
                    QApplication.beep()
                    QApplication.alert(self)
                    # add to Results Tab so it can be played back on demand
                    self.add_comparison_result_signal.emit(result)

                elif get_setting("message_no_cheater_found") != "":
                    timestamp = datetime.now()
                    r1 = result.replay1
                    r2 = result.replay2
                    msg = get_setting("message_no_cheater_found").format(ts=timestamp, similarity=result.similarity,
                                                                      replay1_name=r1.username, replay2_name=r2.username,
                                                                      later_name=result.later_name, replay1_mods=r1.mods,
                                                                      replay2_mods=r2.mods, replay1_id=r1.replay_id,
                                                                      replay2_id=r2.replay_id)
                    self.write(msg)
        except Empty:
            pass

    def visualize(self, replay1, replay2):
        self.visualizer_window = VisualizerWindow(replays=(replay1, replay2))
        self.visualizer_window.show()


class MapTab(QWidget):
    def __init__(self):
        super(MapTab, self).__init__()

        self.info = QLabel(self)
        self.info.setText("Compares the top plays on a Map's leaderboard.\nIf a user is given, "
                          "it will compare that user's play on the map against the other top plays of the map.")

        self.id_combined = IdWidgetCombined()
        self.compare_top = CompareTopUsers()

        self.threshold = Threshold()  # ThresholdCombined()
        layout = QGridLayout()
        layout.addWidget(self.info, 0, 0, 1, 1)
        layout.addWidget(self.id_combined, 1, 0, 2, 1)
        layout.addWidget(self.compare_top, 4, 0, 1, 1)
        layout.addWidget(self.threshold, 5, 0, 1, 1)

        self.setLayout(layout)


class UserTab(QWidget):
    def __init__(self):
        super(UserTab, self).__init__()
        self.info = QLabel(self)
        self.info.setText("Compares each of a user's top plays against that map's leaderboard.")

        self.user_id = InputWidget("User Id", "User id, as seen in the profile url", type_="id")
        self.compare_top_users = CompareTopUsers()
        self.compare_top_map = CompareTopPlays()
        self.threshold = Threshold()  # ThresholdCombined()

        layout = QGridLayout()
        layout.addWidget(self.info, 0, 0, 1, 1)
        layout.addWidget(self.user_id, 1, 0, 1, 1)
        # leave space for inserting the user user top plays widget
        layout.addWidget(self.compare_top_map, 3, 0, 1, 1)
        layout.addWidget(self.compare_top_users, 4, 0, 1, 1)
        layout.addWidget(self.threshold, 5, 0, 1, 1)
        self.layout = layout
        self.setLayout(self.layout)


class LocalTab(QWidget):
    def __init__(self):
        super(LocalTab, self).__init__()
        self.info = QLabel(self)
        self.info.setText("Compares osr files in a given folder.\n"
                          "If a Map is given, it will compare the osrs against the leaderboard of that map.\n"
                          "If both a user and a map are given, it will compare the osrs against the user's "
                          "score on that map.")
        self.folder_chooser = FolderChooser("Replay folder", get_setting("local_replay_dir"))
        self.folder_chooser.path_signal.connect(self.update_dir)
        self.id_combined = IdWidgetCombined()
        self.compare_top = CompareTopUsers()
        self.threshold = Threshold()  # ThresholdCombined()
        self.id_combined.map_id.field.textChanged.connect(self.switch_compare)
        self.switch_compare()

        self.grid = QGridLayout()
        self.grid.addWidget(self.info, 0, 0, 1, 1)
        self.grid.addWidget(self.folder_chooser, 1, 0, 1, 1)
        self.grid.addWidget(self.id_combined, 2, 0, 2, 1)
        self.grid.addWidget(self.compare_top, 4, 0, 1, 1)
        self.grid.addWidget(self.threshold, 5, 0, 1, 1)

        self.setLayout(self.grid)

    def switch_compare(self):
        self.compare_top.update_user(self.id_combined.map_id.field.text() != "")

    def update_dir(self, path):
        update_default("local_replay_dir", path)


class VerifyTab(QWidget):
    def __init__(self):
        super(VerifyTab, self).__init__()
        self.info = QLabel(self)
        self.info.setText("Checks if the given user's replays on a map are steals of each other.")

        self.map_id = InputWidget("Map Id", "Beatmap id, not the mapset id!", type_="id")
        self.user_id_1 = InputWidget("User Id #1", "User id, as seen in the profile url", type_="id")
        self.user_id_2 = InputWidget("User Id #2", "User id, as seen in the profile url", type_="id")

        self.threshold = Threshold()  # ThresholdCombined()

        layout = QGridLayout()
        layout.addWidget(self.info, 0, 0, 1, 1)
        layout.addWidget(self.map_id, 1, 0, 1, 1)
        layout.addWidget(self.user_id_1, 2, 0, 1, 1)
        layout.addWidget(self.user_id_2, 3, 0, 1, 1)
        layout.addWidget(self.threshold, 4, 0, 1, 1)

        self.setLayout(layout)


class SettingsTab(QWidget):
    def __init__(self):
        super(SettingsTab, self).__init__()
        self.qscrollarea = QScrollArea(self)
        self.qscrollarea.setWidget(ScrollableSettingsWidget())
        self.qscrollarea.setAlignment(Qt.AlignCenter)  # center in scroll area - maybe undesirable
        self.qscrollarea.setWidgetResizable(True)

        self.info = QLabel(self)
        self.info.setText(f"Backend Version: {cg_version}<br/>"
                          f"Frontend Version: {__version__}<br/>"
                          f"Found a bug or want to request a feature? "
                          f"Open an issue <a href=\"https://github.com/circleguard/circleguard/issues\">here</a>!")
        self.info.setTextFormat(Qt.RichText)
        self.info.setTextInteractionFlags(Qt.TextBrowserInteraction)
        self.info.setOpenExternalLinks(True)
        self.info.setAlignment(Qt.AlignCenter)

        layout = QVBoxLayout()
        layout.addWidget(self.info)
        layout.addWidget(self.qscrollarea)
        self.setLayout(layout)


class ScrollableSettingsWidget(QFrame):
    """
    This class contains all of the actual settings content - SettingsTab just has a
    QScrollArea wrapped around this widget so that it can be scrolled down.
    """
    def __init__(self):
        super().__init__()
        self._rainbow_speed = 0.005
        self._rainbow_counter = 0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.next_color)
        self.welcome = wizard.WelcomeWindow()
        self.welcome.SetupPage.darkmode.box.stateChanged.connect(switch_theme)
        self.welcome.SetupPage.caching.box.stateChanged.connect(partial(update_default, "caching"))

        self.apikey_widget = InputWidget("Api Key", "", type_="password")
        self.apikey_widget.field.setText(get_setting("api_key"))
        self.apikey_widget.field.textChanged.connect(partial(update_default, "api_key"))

        self.thresh_widget = Threshold()
        self.thresh_widget.spinbox.valueChanged.connect(partial(update_default, "threshold"))

        self.darkmode = OptionWidget("Dark mode", "Come join the dark side")
        self.darkmode.box.stateChanged.connect(switch_theme)

        self.cache = OptionWidget("Caching", "Downloaded replays will be cached locally")
        self.cache.box.stateChanged.connect(partial(update_default, "caching"))

        self.cache_dir = FolderChooser("Cache Path", get_setting("cache_dir"))
        self.cache_dir.path_signal.connect(partial(update_default, "cache_dir"))
        self.cache.box.stateChanged.connect(self.cache_dir.switch_enabled)

        self.loglevel = LoglevelWidget("")
        self.loglevel.level_combobox.currentIndexChanged.connect(self.set_circleguard_loglevel)
        self.set_circleguard_loglevel()  # set the default loglevel in cg, not just in gui

        self.rainbow = OptionWidget("Rainbow mode", ":3")
        self.rainbow.box.stateChanged.connect(self.switch_rainbow)

        self.wizard = ButtonWidget("Run Wizard", "")
        self.wizard.button.clicked.connect(self.show_wizard)

        self.grid = QVBoxLayout()
        self.grid.addWidget(Separator("Circleguard settings"))
        self.grid.addWidget(self.apikey_widget)
        self.grid.addWidget(self.thresh_widget)
        self.grid.addWidget(self.cache)
        self.grid.addWidget(self.cache_dir)
        self.grid.addWidget(Separator("GUI settings"))
        self.grid.addWidget(self.darkmode)
        self.grid.addWidget(Separator("Debug settings"))
        self.grid.addWidget(self.loglevel)
        self.grid.addWidget(ResetSettings())
        self.grid.addWidget(self.wizard)
        self.grid.addWidget(Separator("Experiments"))
        self.grid.addWidget(self.rainbow)
        self.grid.addWidget(BeatmapTest())
        self.grid.addWidget(Separator("String Format settings"))
        self.grid.addWidget(StringFormatWidget(""))

        self.setLayout(self.grid)

        old_theme = get_setting("dark_theme")  # this is needed because switch_theme changes the setting
        self.darkmode.box.setChecked(-1)  # force-runs switch_theme if the DARK_THEME is False
        self.darkmode.box.setChecked(old_theme)
        self.cache.box.setChecked(get_setting("caching"))
        self.cache_dir.switch_enabled(get_setting("caching"))
        self.rainbow.box.setChecked(get_setting("rainbow_accent"))

    def set_circleguard_loglevel(self):
        set_options(loglevel=self.loglevel.level_combobox.currentData())

    def next_color(self):
        (r, g, b) = colorsys.hsv_to_rgb(self._rainbow_counter, 1.0, 1.0)
        color = QColor(int(255 * r), int(255 * g), int(255 * b))
        switch_theme(get_setting("dark_theme"), color)
        self._rainbow_counter += self._rainbow_speed
        if self._rainbow_counter >= 1:
            self._rainbow_counter = 0

    def switch_rainbow(self, state):
        update_default("rainbow_accent", 1 if state else 0)
        if get_setting("rainbow_accent"):
            self.timer.start(1000/15)
        else:
            self.timer.stop()
            switch_theme(get_setting("dark_theme"))

    def show_wizard(self):
        self.welcome.show()


class ResultsTab(QWidget):
    def __init__(self):
        super(ResultsTab, self).__init__()

        _layout = QVBoxLayout()
        self.qscrollarea = QScrollArea(self)
        self.results = ResultsFrame()
        self.qscrollarea.setWidget(self.results)
        self.qscrollarea.setWidgetResizable(True)

        # we want widgets to fill from top down,
        # being vertically centered looks weird
        _layout.addWidget(self.qscrollarea)
        self.setLayout(_layout)


class ResultsFrame(QFrame):
    def __init__(self):
        super(ResultsFrame, self).__init__()
        self.layout = QVBoxLayout()
        self.layout.setAlignment(Qt.AlignTop)
        self.info_label = QLabel("After running Comparisons, this tab will fill up with results")
        self.layout.addWidget(self.info_label)
        self.setLayout(self.layout)


def switch_theme(dark, accent=QColor(71, 174, 247)):
    update_default("dark_theme", 1 if dark else 0)
    if dark:
        dark_p = QPalette()

        dark_p.setColor(QPalette.Window, QColor(53, 53, 53))
        dark_p.setColor(QPalette.WindowText, Qt.white)
        dark_p.setColor(QPalette.Base, QColor(25, 25, 25))
        dark_p.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
        dark_p.setColor(QPalette.ToolTipBase, QColor(53, 53, 53))
        dark_p.setColor(QPalette.ToolTipText, Qt.white)
        dark_p.setColor(QPalette.Text, Qt.white)
        dark_p.setColor(QPalette.Button, QColor(53, 53, 53))
        dark_p.setColor(QPalette.ButtonText, Qt.white)
        dark_p.setColor(QPalette.BrightText, Qt.red)
        dark_p.setColor(QPalette.Highlight, accent)
        dark_p.setColor(QPalette.Inactive, QPalette.Highlight, Qt.lightGray)
        dark_p.setColor(QPalette.HighlightedText, Qt.black)
        dark_p.setColor(QPalette.Disabled, QPalette.Text, Qt.darkGray)
        dark_p.setColor(QPalette.Disabled, QPalette.ButtonText, Qt.darkGray)
        dark_p.setColor(QPalette.Disabled, QPalette.Highlight, Qt.darkGray)
        dark_p.setColor(QPalette.Disabled, QPalette.Base, QColor(53, 53, 53))
        dark_p.setColor(QPalette.Link, accent)
        dark_p.setColor(QPalette.LinkVisited, accent)

        app.setPalette(dark_p)
        app.setStyleSheet("QToolTip { color: #ffffff; "
                          "background-color: #2a2a2a; "
                          "border: 1px solid white; }"
                          "QLabel {font-weight: Normal; }")
    else:
        app.setPalette(app.style().standardPalette())
        updated_palette = QPalette()
        # fixes inactive items not being greyed out
        updated_palette.setColor(QPalette.Disabled, QPalette.ButtonText, Qt.darkGray)
        updated_palette.setColor(QPalette.Highlight, accent)
        updated_palette.setColor(QPalette.Disabled, QPalette.Highlight, Qt.darkGray)
        updated_palette.setColor(QPalette.Inactive, QPalette.Highlight, Qt.darkGray)
        updated_palette.setColor(QPalette.Link, accent)
        updated_palette.setColor(QPalette.LinkVisited, accent)
        app.setPalette(updated_palette)
        app.setStyleSheet("QToolTip { color: #000000; "
                          "background-color: #D5D5D5; "
                          "border: 1px solid white; }"
                          "QLabel {font-weight: Normal; }")


if __name__ == "__main__":
    # create and open window
    app = QApplication([])
    app.setStyle("Fusion")
    WINDOW = WindowWrapper()
    set_event_window(WINDOW)
    WINDOW.resize(600, 500)
    WINDOW.show()
    if not (str(get_setting("ran")).lower() == "true"):
        welcome = wizard.WelcomeWindow()
        welcome.SetupPage.darkmode.box.stateChanged.connect(switch_theme)
        welcome.SetupPage.caching.box.stateChanged.connect(partial(update_default,"caching"))
        welcome.show()
        update_default("ran", True)
    app.exec_()
