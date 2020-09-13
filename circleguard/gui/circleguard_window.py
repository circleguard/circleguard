import logging
from logging.handlers import RotatingFileHandler
import os
from functools import partial
import threading
from datetime import datetime, timedelta
import re

from PyQt5.QtWidgets import (QMainWindow, QShortcut, QApplication,
    QProgressBar, QLabel, QTextEdit)
from PyQt5.QtCore import Qt, QObject, pyqtSignal, QTimer
from PyQt5.QtGui import QIcon, QPalette, QColor, QKeySequence
# from circleguard import (ReplayMap, Circleguard)
from packaging import version
# import requests
# from requests import RequestException

from settings import LinkableSetting, get_setting, set_setting, overwrite_config
from widgets import WidgetCombiner, ResultW
from .gui import MainWidget, DebugWindow
from utils import (resource_path, AnalysisResult, URLAnalysisResult,
    ACCENT_COLOR, StealResult, RelaxResult, CorrectionResult, TimewarpResult)
from version import __version__


# logging methodology heavily adapted from https://stackoverflow.com/q/28655198/
class Handler(QObject, logging.Handler):
    new_message = pyqtSignal(object)

    def __init__(self):
        super().__init__()

    def emit(self, record):
        message = self.format(record)
        # replace api keys with asterisks if they get into the logs from eg a
        # stacktrace
        api_key = get_setting("api_key")
        message = message.replace(api_key, "*"*len(api_key))
        self.new_message.emit(message)

class CircleguardWindow(LinkableSetting, QMainWindow):
    def __init__(self, app):
        QMainWindow.__init__(self)
        LinkableSetting.__init__(self, ["log_save", "theme"])
        # our QApplication, so we can set the theme from our widgets
        self.app = app

        # set the theme before initializing anything so it gets applied
        self.on_setting_changed("theme", self.setting_values["theme"])

        self.clipboard = QApplication.clipboard()
        self.progressbar = QProgressBar()
        self.progressbar.setFixedWidth(250)
        self.current_state_label = QLabel("Idle")
        self.current_state_label.setTextFormat(Qt.RichText)
        self.current_state_label.setTextInteractionFlags(Qt.TextBrowserInteraction)
        self.current_state_label.setOpenExternalLinks(True)
        # statusBar() is a qt function that will create a status bar tied to the window
        # if it doesnt exist, and access the existing one if it does.
        self.statusBar().addWidget(WidgetCombiner(self.progressbar, self.current_state_label, self))
        self.statusBar().setSizeGripEnabled(False)
        self.statusBar().setContentsMargins(8, 2, 10, 2)

        self.main_window = MainWidget()
        self.main_window.analysis_selection.set_progressbar_signal.connect(self.set_progressbar)
        self.main_window.analysis_selection.increment_progressbar_signal.connect(self.increment_progressbar)
        self.main_window.analysis_selection.update_label_signal.connect(self.update_label)

        # we reference this widget a lot, so shorten its reference as a
        # convenience
        self.cg_classic = self.main_window.cg_classic

        self.cg_classic.main_tab.set_progressbar_signal.connect(self.set_progressbar)
        self.cg_classic.main_tab.increment_progressbar_signal.connect(self.increment_progressbar)
        self.cg_classic.main_tab.update_label_signal.connect(self.update_label)
        self.cg_classic.main_tab.add_result_signal.connect(self.add_result)
        self.cg_classic.main_tab.add_url_analysis_result_signal.connect(self.add_url_analysis_result)
        self.cg_classic.main_tab.add_run_to_queue_signal.connect(self.add_run_to_queue)
        self.cg_classic.main_tab.update_run_status_signal.connect(self.update_run_status)
        self.cg_classic.queue_tab.cancel_run_signal.connect(self.cancel_run)


        self.setCentralWidget(self.main_window)
        QShortcut(QKeySequence(Qt.CTRL + Qt.Key_Right), self, self.tab_right)
        QShortcut(QKeySequence(Qt.CTRL + Qt.Key_Left), self, self.tab_left)
        QShortcut(QKeySequence(Qt.CTRL + Qt.Key_Q), self, app.quit)

        self.setWindowTitle(f"Circleguard v{__version__}")
        self.setWindowIcon(QIcon(resource_path("logo/logo.ico")))
        self.start_timer()
        self.debug_window = None

        formatter = logging.Formatter(get_setting("log_format"), datefmt=get_setting("timestamp_format"))
        handler = Handler()
        handler.setFormatter(formatter)
        handler.new_message.connect(self.log)

        log_dir = get_setting("log_dir")
        log_file = os.path.join(log_dir, "circleguard.log")
        # 1 mb max file size, with 3 rotating files.
        self.file_handler = RotatingFileHandler(log_file, maxBytes=10**6, backupCount=3)
        self.file_handler.setFormatter(formatter)

        logging.getLogger("circleguard").addHandler(handler)
        logging.getLogger("circleguard").addHandler(self.file_handler)
        logging.getLogger("ossapi").addHandler(handler)
        logging.getLogger("ossapi").addHandler(self.file_handler)
        logging.getLogger("circleguard_gui").addHandler(handler)
        logging.getLogger("circleguard_gui").addHandler(self.file_handler)

        self.on_setting_changed("log_save", self.setting_values["log_save"])

        self.thread = threading.Thread(target=self.run_update_check)
        self.thread.start()

    def on_setting_changed(self, setting, new_value):
        if setting == "log_save":
            if not new_value:
                self.file_handler.setLevel(51) # same as disabling the handler (CRITICAL=50)
            else:
                self.file_handler.setLevel(logging.NOTSET) # same as default (passes all records to the attached logger)
        elif setting == "theme":
            self.switch_theme(new_value)

    def tab_right(self):
        tabs = self.cg_classic.tabs
        tabs.setCurrentIndex(tabs.currentIndex() + 1)

    def tab_left(self):
        tabs = self.cg_classic.tabs
        tabs.setCurrentIndex(tabs.currentIndex() - 1)

    def mousePressEvent(self, event):
        focused = self.focusWidget()
        if focused is not None and not isinstance(focused, QTextEdit):
            focused.clearFocus()
        super().mousePressEvent(event)

    def url_scheme_called(self, url):
        from circleguard import ReplayMap, Circleguard
        # url is bytes, so decode back to str
        url = url.decode()
        # windows appends an extra slash even if the original url didn't have
        # it, so remove it
        url = url.strip("/")
        # all urls take one of the following forms:
        # * circleguard://m=221777&u=2757689&t=15000
        # * circleguard://m=221777&u=2757689
        # * circleguard://m=221777&u=2757689&u2=3219026
        map_id = re.compile(r"m=(.*?)(&|$)").search(url).group(1)
        user_id = re.compile(r"u=(.*?)(&|$)").search(url).group(1)
        timestamp_match = re.compile(r"t=(.*?)(&|$)").search(url)
        # start at the beginning if timestamp isn't specified
        timestamp = int(timestamp_match.group(1)) if timestamp_match else 0

        user_id_2_match = re.compile(r"u2=(.*?)(&|$)").search(url)
        user_id_2 = None
        if user_id_2_match:
            user_id_2 = user_id_2_match.group(1)

        r = ReplayMap(map_id, user_id)
        cg = Circleguard(get_setting("api_key"))
        cg.load(r)
        replays = [r]

        if user_id_2:
            r2 = ReplayMap(map_id, user_id_2)
            cg.load(r2)
            replays.append(r2)
        # open visualizer for the given map and user, and jump to the timestamp
        result = URLAnalysisResult(replays, timestamp)
        self.cg_classic.main_tab.url_analysis_q.put(result)

    def start_timer(self):
        timer = QTimer(self)
        timer.timeout.connect(self.run_timer)
        timer.start(250)

    def run_timer(self):
        """
        check for stderr messages (because logging prints to stderr not stdout, and
        it's nice to have stdout reserved) and then print cg results
        """
        self.cg_classic.main_tab.print_results()
        self.cg_classic.main_tab.check_circleguard_queue()

    def log(self, message):
        """
        Message is the string message sent to the io stream
        """

        log_output = get_setting("_log_output")
        if log_output in ["terminal", "both"]:
            self.cg_classic.main_tab.write(message)

        if log_output in ["new_window", "both"]:
            if self.debug_window and self.debug_window.isVisible():
                self.debug_window.write(message)
            else:
                self.debug_window = DebugWindow()
                self.debug_window.show()
                self.debug_window.write(message)

    def update_label(self, text):
        self.current_state_label.setText(text)

    def run_update_check(self):
        last_check = datetime.strptime(get_setting("last_update_check"), get_setting("timestamp_format"))
        next_check = last_check + timedelta(hours=1)
        if next_check > datetime.now():
            self.update_label(self.get_version_update_str())
            return
        try:
            import requests
            from requests import RequestException
            # check for new version
            git_request = requests.get("https://api.github.com/repos/circleguard/circleguard/releases/latest").json()
            git_version = version.parse(git_request["name"])
            set_setting("latest_version", git_version)
            set_setting("last_update_check", datetime.now().strftime(get_setting("timestamp_format")))
        except RequestException:
            # user is probably offline
            pass
        self.update_label(self.get_version_update_str())


    def get_version_update_str(self):
        current_version = version.parse(__version__)
        if current_version < version.parse(get_setting("latest_version")):
            return "<a href=\'https://github.com/circleguard/circleguard/releases/latest'>Update available!</a>"
        else:
            return "Idle"

    def increment_progressbar(self, increment):
        self.progressbar.setValue(self.progressbar.value() + increment)

    def set_progressbar(self, max_value):
        # if -1, reset progressbar and remove its text
        if max_value == -1:
            # removes cases where range was set to (0,0)
            self.progressbar.setRange(0, 1)
            # remove ``0%`` text on the progressbar (doesn't look good)
            self.progressbar.reset()
            return
        self.progressbar.setValue(0)
        self.progressbar.setRange(0, max_value)

    def add_result(self, result):
        # this function right here could very well lead to some memory issues.
        # I tried to avoid leaving a reference to result's replays in this
        # method, but it's quite possible things are still not very clean.
        # Ideally only ResultW would have a reference to the two replays, and
        # nothing else.
        timestamp = datetime.now()
        label_text = None
        template_text = None

        if isinstance(result, StealResult):
            circleguard_url = f"circleguard://m={result.replay1.map_id}&u={result.replay1.user_id}&u2={result.replay2.user_id}"
            label_text = get_setting("string_result_steal").format(ts=timestamp, similarity=result.similarity, r=result, r1=result.replay1, r2=result.replay2,
                                        earlier_replay_mods_short_name=result.earlier_replay.mods.short_name(), earlier_replay_mods_long_name=result.earlier_replay.mods.long_name(),
                                        later_replay_mods_short_name=result.later_replay.mods.short_name(), later_replay_mods_long_name=result.later_replay.mods.long_name())
            template_text = get_setting("template_steal").format(ts=timestamp, similarity=result.similarity, r=result, r1=result.replay1, r2=result.replay2,
                                        earlier_replay_mods_short_name=result.earlier_replay.mods.short_name(), earlier_replay_mods_long_name=result.earlier_replay.mods.long_name(),
                                        later_replay_mods_short_name=result.later_replay.mods.short_name(), later_replay_mods_long_name=result.later_replay.mods.long_name(),
                                        circleguard_url=circleguard_url)
            replays = [result.replay1, result.replay2]

        elif isinstance(result, RelaxResult):
            circleguard_url = f"circleguard://m={result.replay.map_id}&u={result.replay.user_id}"
            label_text = get_setting("string_result_relax").format(ts=timestamp, ur=result.ur, r=result,
                                        replay=result.replay, mods_short_name=result.replay.mods.short_name(),
                                        mods_long_name=result.replay.mods.long_name())
            template_text = get_setting("template_relax").format(ts=timestamp, ur=result.ur, r=result,
                                        replay=result.replay, mods_short_name=result.replay.mods.short_name(),
                                        mods_long_name=result.replay.mods.long_name(), circleguard_url=circleguard_url)
            replays = [result.replay]
        elif isinstance(result, CorrectionResult):
            circleguard_url = f"circleguard://m={result.replay.map_id}&u={result.replay.user_id}"
            label_text = get_setting("string_result_correction").format(ts=timestamp, r=result, num_snaps=len(result.snaps), replay=result.replay,
                                        mods_short_name=result.replay.mods.short_name(), mods_long_name=result.replay.mods.long_name())

            snap_table = ("| Time (ms) | Angle (°) | Distance (px) |\n"
                            "| :-: | :-: | :-: |\n")
            for snap in result.snaps:
                snap_table += "| {:.0f} | {:.2f} | {:.2f} |\n".format(snap.time, snap.angle, snap.distance)
            template_text = get_setting("template_correction").format(ts=timestamp, r=result, replay=result.replay, snap_table=snap_table,
                                        mods_short_name=result.replay.mods.short_name(), mods_long_name=result.replay.mods.long_name(),
                                        circleguard_url=circleguard_url)
            replays = [result.replay]
        elif isinstance(result, TimewarpResult):
            circleguard_url = f"circleguard://m={result.replay.map_id}&u={result.replay.user_id}"
            label_text = get_setting("string_result_timewarp").format(ts=timestamp, r=result, replay=result.replay, frametime=result.frametime,
                                        mods_short_name=result.replay.mods.short_name(), mods_long_name=result.replay.mods.long_name())
            template_text = get_setting("template_timewarp").format(ts=timestamp, r=result, frametime=result.frametime,
                                        mods_short_name=result.replay.mods.short_name(), mods_long_name=result.replay.mods.long_name(),
                                        circleguard_url=circleguard_url)
            replays = [result.replay]
        elif isinstance(result, AnalysisResult):
            replays = result.replays
            # special case that occurs often, we can show more info if there's only a single replay
            if len(replays) == 1:
                r = replays[0]
                label_text = get_setting("string_result_visualization_single").format(ts=timestamp, replay=r, mods_short_name=r.mods.short_name(),
                                        mods_long_name=r.mods.long_name())
            else:
                label_text = get_setting("string_result_visualization").format(ts=timestamp, replay_amount=len(result.replays), map_id=result.replays[0].map_id)

        result_widget = ResultW(label_text, result, replays)
        # set button signal connections (visualize and copy template to clipboard)
        result_widget.visualize_button_pressed_signal.connect(partial(self.cg_classic.main_tab.visualize, result_widget.replays, result_widget.replays[0].map_id, result_widget.result))
        result_widget.template_button_pressed_signal.connect(partial(self.copy_to_clipboard, template_text))
        # remove info text if shown
        if not self.cg_classic.results_tab.results.info_label.isHidden():
            self.cg_classic.results_tab.results.info_label.hide()
        self.cg_classic.results_tab.results.layout.insertWidget(0, result_widget)

    def add_url_analysis_result(self, result):
        self.cg_classic.main_tab.visualize_from_url(result)

    def copy_to_clipboard(self, text):
        self.clipboard.setText(text)

    def add_run_to_queue(self, run):
        self.cg_classic.queue_tab.add_run(run)

    def update_run_status(self, run_id, status):
        self.cg_classic.queue_tab.update_status(run_id, status)

    def cancel_run(self, run_id):
        self.cg_classic.main_tab.runs[run_id].event.set()

    def cancel_all_runs(self):
        """called when lastWindowClosed signal emits. Cancel all our runs so
        we don't hang the application on loading/comparing while trying to quit"""
        for run in self.cg_classic.main_tab.runs:
            run.event.set()

    def on_application_quit(self):
        """
        Called when the app.aboutToQuit signal is emitted.
        """
        if self.debug_window is not None:
            self.debug_window.close()
        if self.cg_classic.main_tab.visualizer is not None:
            self.cg_classic.main_tab.visualizer.close()
        overwrite_config()

    def switch_theme(self, theme):
        if theme == "dark":
            DARK_GREY = QColor(53, 53, 53)

            dark_p = QPalette()

            dark_p.setColor(QPalette.Window, DARK_GREY)
            dark_p.setColor(QPalette.WindowText, Qt.white)
            dark_p.setColor(QPalette.Base, QColor(25, 25, 25))
            dark_p.setColor(QPalette.AlternateBase, DARK_GREY)
            dark_p.setColor(QPalette.ToolTipBase, DARK_GREY)
            dark_p.setColor(QPalette.ToolTipText, Qt.white)
            dark_p.setColor(QPalette.Text, Qt.white)
            dark_p.setColor(QPalette.Button, DARK_GREY)
            dark_p.setColor(QPalette.ButtonText, Qt.white)
            dark_p.setColor(QPalette.BrightText, Qt.red)
            dark_p.setColor(QPalette.Highlight, ACCENT_COLOR)
            dark_p.setColor(QPalette.Inactive, QPalette.Highlight, Qt.lightGray)
            dark_p.setColor(QPalette.HighlightedText, Qt.black)
            dark_p.setColor(QPalette.Disabled, QPalette.Text, Qt.darkGray)
            dark_p.setColor(QPalette.Disabled, QPalette.ButtonText, Qt.darkGray)
            dark_p.setColor(QPalette.Disabled, QPalette.Highlight, Qt.darkGray)
            dark_p.setColor(QPalette.Disabled, QPalette.Base, DARK_GREY)
            dark_p.setColor(QPalette.Link, ACCENT_COLOR)
            dark_p.setColor(QPalette.LinkVisited, ACCENT_COLOR)

            # the `bigButton` class is necessary because qt (or the fusion
            # style, not sure which) is putting a *gradient* on the buttons by
            # by default. Kind of crazy if you ask me, but it does make the
            # small buttons look good, so I only want to change it to a flat
            # color for larger buttons (and also round their corners because
            # large buttons don't look so good when they're blocky)

            self.app.setPalette(dark_p)
            self.app.setStyleSheet("""
                QToolTip {
                    color: #ffffff;
                    background-color: #2a2a2a;
                    border: 1px solid white;
                }
                QPushButton#bigButton {
                    background-color: rgb(64, 64, 64);
                    padding: 4px;
                    border: 1px solid rgb(25, 25, 25);
                    border-radius: 15%;
                }
                QPushButton#bigButton:hover {
                    background-color: rgb(67, 67, 67);
                }
                QPushButton#bigButton:pressed {
                    background-color: rgb(61, 61, 61);
                }
                QPushButton#backButton {
                    margin-top: 5px;
                    margin-left: 10px;
                }
                QLabel {
                    font-weight: Normal;
                }
                QTextEdit {
                    background-color: #212121;
                }
                LoadableW, CheckW, DragWidget, ReplayMapVis {
                    border: 1.5px solid #272727;
                }
                ReplayMapCreation {
                    border: 1.5px solid #1f1f1f;
                }
                """)
        else:
            self.app.setPalette(self.app.style().standardPalette())
            updated_palette = QPalette()
            # fixes inactive items not being greyed out
            updated_palette.setColor(QPalette.Disabled, QPalette.ButtonText, Qt.darkGray)
            updated_palette.setColor(QPalette.Highlight, ACCENT_COLOR)
            updated_palette.setColor(QPalette.Disabled, QPalette.Highlight, Qt.darkGray)
            updated_palette.setColor(QPalette.Inactive, QPalette.Highlight, Qt.darkGray)
            updated_palette.setColor(QPalette.Link, ACCENT_COLOR)
            updated_palette.setColor(QPalette.LinkVisited, ACCENT_COLOR)
            self.app.setPalette(updated_palette)
            self.app.setStyleSheet("""
                QToolTip {
                    color: #000000;
                    background-color: #D5D5D5;
                    border: 1px solid white;
                }
                QPushButton#backButton {
                    margin-top: 5px;
                    margin-left: 10px;
                }
                QLabel {
                    font-weight: Normal;
                }
                LoadableW, CheckW, DragWidget {
                    border: 1.5px solid #bfbfbf;
                }
                """)
