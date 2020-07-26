import logging
from logging.handlers import RotatingFileHandler
import os
from functools import partial
import threading
from datetime import datetime, timedelta
import re

from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from circleguard import *
from packaging import version
import requests
from requests import RequestException

from settings import LinkableSetting, get_setting, set_setting, overwrite_config
from widgets import WidgetCombiner, ResultW
from .gui import MainWindow, DebugWindow
from utils import resource_path, AnalysisResult, URLAnalysisResult
from version import __version__


# logging methodology heavily adapted from https://stackoverflow.com/q/28655198/
class Handler(QObject, logging.Handler):
    new_message = pyqtSignal(object)

    def __init__(self):
        super().__init__()

    def emit(self, record):
        message = self.format(record)
        self.new_message.emit(message)

class CircleguardWindow(LinkableSetting, QMainWindow):
    def __init__(self, app):
        QMainWindow.__init__(self)
        LinkableSetting.__init__(self, ["log_save", "theme"])
        # our QApplication, so we can set the theme from our widgets
        self.app = app
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

        self.main_window = MainWindow(self)
        self.main_window.main_tab.set_progressbar_signal.connect(self.set_progressbar)
        self.main_window.main_tab.increment_progressbar_signal.connect(self.increment_progressbar)
        self.main_window.main_tab.update_label_signal.connect(self.update_label)
        self.main_window.main_tab.add_result_signal.connect(self.add_result)
        self.main_window.main_tab.add_url_analysis_result_signal.connect(self.add_url_analysis_result)
        self.main_window.main_tab.add_run_to_queue_signal.connect(self.add_run_to_queue)
        self.main_window.main_tab.update_run_status_signal.connect(self.update_run_status)
        self.main_window.queue_tab.cancel_run_signal.connect(self.cancel_run)

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
        # apply setting values on application start
        self.on_setting_changed("log_save", self.setting_values["log_save"])
        self.on_setting_changed("theme", self.setting_values["theme"])

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
        tabs = self.main_window.tabs
        tabs.setCurrentIndex(tabs.currentIndex() + 1)

    def tab_left(self):
        tabs = self.main_window.tabs
        tabs.setCurrentIndex(tabs.currentIndex() - 1)

    def mousePressEvent(self, event):
        focused = self.focusWidget()
        if focused is not None and not isinstance(focused, QTextEdit):
            focused.clearFocus()
        super().mousePressEvent(event)

    def url_scheme_called(self, url):
        # url is bytes, so decode back to str
        url = url.decode()
        # windows appends an extra slash even if the original url didn't have 
        # it, so remove it
        url = url.strip("/")
        # all urls are of the form circleguard://m=221777&u=2757689&t=150000
        map_id = re.compile(r"m=(.*?)(&|$)").search(url).group(1)
        user_id = re.compile(r"u=(.*?)(&|$)").search(url).group(1)
        timestamp = int(re.compile(r"t=(.*?)(&|$)").search(url).group(1))

        r = ReplayMap(map_id, user_id)
        cg = Circleguard(get_setting("api_key"))
        cg.load(r)

        # open visualizer for the given map and user, and jump to the timestamp
        result = URLAnalysisResult([r], timestamp)
        self.main_window.main_tab.url_analysis_q.put(result)
        pass

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
        self.main_window.main_tab.check_circleguard_queue()

    def log(self, message):
        """
        Message is the string message sent to the io stream
        """

        log_output = get_setting("_log_output")
        if log_output in ["terminal", "both"]:
            self.main_window.main_tab.write(message)

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
            return "<a href=\'https://circleguard.dev/download'>Update available!</a>"
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
            label_text = get_setting("string_result_steal").format(ts=timestamp, similarity=result.similarity, r=result, r1=result.replay1, r2=result.replay2,
                                        earlier_replay_mods_short_name=result.earlier_replay.mods.short_name(), earlier_replay_mods_long_name=result.earlier_replay.mods.long_name(),
                                        later_replay_mods_short_name=result.later_replay.mods.short_name(), later_replay_mods_long_name=result.later_replay.mods.long_name())
            template_text = get_setting("template_steal").format(ts=timestamp, similarity=result.similarity, r=result, r1=result.replay1, r2=result.replay2,
                                        earlier_replay_mods_short_name=result.earlier_replay.mods.short_name(), earlier_replay_mods_long_name=result.earlier_replay.mods.long_name(),
                                        later_replay_mods_short_name=result.later_replay.mods.short_name(), later_replay_mods_long_name=result.later_replay.mods.long_name())
            replays = [result.replay1, result.replay2]

        elif isinstance(result, RelaxResult):
            label_text = get_setting("string_result_relax").format(ts=timestamp, ur=result.ur, r=result,
                                        replay=result.replay, mods_short_name=result.replay.mods.short_name(),
                                        mods_long_name=result.replay.mods.long_name())
            template_text = get_setting("template_relax").format(ts=timestamp, ur=result.ur, r=result,
                                        replay=result.replay, mods_short_name=result.replay.mods.short_name(),
                                        mods_long_name=result.replay.mods.long_name())
            replays = [result.replay]
        elif isinstance(result, CorrectionResult):
            label_text = get_setting("string_result_correction").format(ts=timestamp, r=result, num_snaps=len(result.snaps), replay=result.replay,
                                        mods_short_name=result.replay.mods.short_name(), mods_long_name=result.replay.mods.long_name())

            snap_table = ("| Time (ms) | Angle (°) | Distance (px) |\n"
                            "| :-: | :-: | :-: |\n")
            for snap in result.snaps:
                snap_table += "| {:.0f} | {:.2f} | {:.2f} |\n".format(snap.time, snap.angle, snap.distance)
            template_text = get_setting("template_correction").format(ts=timestamp, r=result, replay=result.replay, snap_table=snap_table,
                                        mods_short_name=result.replay.mods.short_name(), mods_long_name=result.replay.mods.long_name())
            replays = [result.replay]
        elif isinstance(result, TimewarpResult):
            label_text = get_setting("string_result_timewarp").format(ts=timestamp, r=result, replay=result.replay, frametime=result.frametime,
                                        mods_short_name=result.replay.mods.short_name(), mods_long_name=result.replay.mods.long_name())
            template_text = get_setting("template_timewarp").format(ts=timestamp, r=result, frametime=result.frametime,
                                        mods_short_name=result.replay.mods.short_name(), mods_long_name=result.replay.mods.long_name())
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
        result_widget.visualize_button_pressed_signal.connect(partial(self.main_window.main_tab.visualize, result_widget.replays, result_widget.replays[0].map_id, result_widget.result))
        result_widget.template_button_pressed_signal.connect(partial(self.copy_to_clipboard, template_text))
        # remove info text if shown
        if not self.main_window.results_tab.results.info_label.isHidden():
            self.main_window.results_tab.results.info_label.hide()
        self.main_window.results_tab.results.layout.insertWidget(0,result_widget)

    def add_url_analysis_result(self, result):
        self.main_window.main_tab.visualize(result.replays, result.replays[0].map_id, result, start_at=result.timestamp)

    def copy_to_clipboard(self, text):
        self.clipboard.setText(text)

    def add_run_to_queue(self, run):
        self.main_window.queue_tab.add_run(run)

    def update_run_status(self, run_id, status):
        self.main_window.queue_tab.update_status(run_id, status)

    def cancel_run(self, run_id):
        self.main_window.main_tab.runs[run_id].event.set()

    def cancel_all_runs(self):
        """called when lastWindowClosed signal emits. Cancel all our runs so
        we don't hang the application on loading/comparing while trying to quit"""
        for run in self.main_window.main_tab.runs:
            run.event.set()

    def on_application_quit(self):
        """
        Called when the app.aboutToQuit signal is emitted.
        """
        if self.debug_window is not None:
            self.debug_window.close()
        if self.main_window.main_tab.visualizer is not None:
            self.main_window.main_tab.visualizer.close()
        overwrite_config()

    def switch_theme(self, theme):
        accent = QColor(71, 174, 247)
        if theme == "dark":
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

            self.app.setPalette(dark_p)
            self.app.setStyleSheet("""
                    QToolTip {
                        color: #ffffff;
                        background-color: #2a2a2a;
                        border: 1px solid white;
                    }
                    QLabel {
                            font-weight: Normal;
                    }
                    QTextEdit {
                            background-color: #212121;
                    }
                    LoadableW {
                            border: 1.5px solid #272727;
                    }
                    CheckW {
                            border: 1.5px solid #272727;
                    }
                    DragWidget {
                            border: 1.5px solid #272727;
                    }""")
        else:
            self.app.setPalette(self.app.style().standardPalette())
            updated_palette = QPalette()
            # fixes inactive items not being greyed out
            updated_palette.setColor(QPalette.Disabled, QPalette.ButtonText, Qt.darkGray)
            updated_palette.setColor(QPalette.Highlight, accent)
            updated_palette.setColor(QPalette.Disabled, QPalette.Highlight, Qt.darkGray)
            updated_palette.setColor(QPalette.Inactive, QPalette.Highlight, Qt.darkGray)
            updated_palette.setColor(QPalette.Link, accent)
            updated_palette.setColor(QPalette.LinkVisited, accent)
            self.app.setPalette(updated_palette)
            self.app.setStyleSheet("""
                    QToolTip {
                        color: #000000;
                        background-color: #D5D5D5;
                        border: 1px solid white;
                    }
                    QLabel {
                        font-weight: Normal;
                    }
                    LoadableW {
                        border: 1.5px solid #bfbfbf;
                    }
                    CheckW {
                        border: 1.5px solid #bfbfbf;
                    }
                    DragWidget {
                        border: 1.5px solid #bfbfbf;
                    }""")
