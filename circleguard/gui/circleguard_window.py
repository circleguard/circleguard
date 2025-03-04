import logging
import os
import re
import threading
from datetime import datetime, timedelta
from functools import partial
from logging.handlers import RotatingFileHandler

from packaging import version
from PyQt6.QtCore import QKeyCombination, QObject, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QIcon, QKeySequence, QPalette, QShortcut
from PyQt6.QtWidgets import QApplication, QLabel, QMainWindow, QProgressBar, QTextEdit
from settings import (
    LinkableSetting,
    get_setting,
    get_setting_raw,
    overwrite_config,
    set_setting,
    set_setting_raw,
)
from utils import (
    ACCENT_COLOR,
    AnalysisResult,
    CorrectionResult,
    RelaxResult,
    StealResult,
    TimewarpResult,
    URLAnalysisResult,
    resource_path,
)
from version import __version__
from widgets import ResultW, WidgetCombiner

from .gui import DebugWindow, MainWidget


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
        message = message.replace(api_key, "*" * len(api_key))
        self.new_message.emit(message)


class CircleguardWindow(LinkableSetting, QMainWindow):
    INSTANCE = None

    def __init__(self, app):
        if CircleguardWindow.INSTANCE is not None:
            raise Exception("CirclegaurdWindow may only be instantiated once!")

        QMainWindow.__init__(self)
        LinkableSetting.__init__(self, ["log_save", "theme"])

        # the circleguard window is our main window and it is sometimes useful
        # for other widgets to be able to interact with the main window
        # instance. Save ourself as a static var so other classes can access us.
        CircleguardWindow.INSTANCE = self
        # our QApplication, so we can set the theme from our widgets
        self.app = app

        # set the theme before initializing anything so it gets applied
        self.on_setting_changed("theme", self.setting_values["theme"])

        self.clipboard = QApplication.clipboard()
        self.progressbar = QProgressBar()
        self.progressbar.setFixedWidth(250)
        self.current_state_label = QLabel("Idle")
        self.current_state_label.setTextFormat(Qt.TextFormat.RichText)
        self.current_state_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextBrowserInteraction
        )
        self.current_state_label.setOpenExternalLinks(True)
        # statusBar() is a qt function that will create a status bar tied to the window
        # if it doesnt exist, and access the existing one if it does.
        self.statusBar().addWidget(
            WidgetCombiner(self.progressbar, self.current_state_label, self)
        )
        self.statusBar().setSizeGripEnabled(False)
        self.statusBar().setContentsMargins(8, 2, 10, 2)

        self.main_window = MainWidget()
        self.main_window.analysis_selection.set_progressbar_signal.connect(
            self.set_progressbar
        )
        self.main_window.analysis_selection.increment_progressbar_signal.connect(
            self.increment_progressbar
        )
        self.main_window.analysis_selection.update_label_signal.connect(
            self.update_label
        )

        # we reference this widget a lot, so shorten its reference as a
        # convenience
        self.cg_classic = self.main_window.cg_classic

        self.cg_classic.main_tab.set_progressbar_signal.connect(self.set_progressbar)
        self.cg_classic.main_tab.increment_progressbar_signal.connect(
            self.increment_progressbar
        )
        self.cg_classic.main_tab.update_label_signal.connect(self.update_label)
        self.cg_classic.main_tab.add_result_signal.connect(self.add_result)
        self.cg_classic.main_tab.add_url_analysis_result_signal.connect(
            self.add_url_analysis_result
        )
        self.cg_classic.main_tab.add_run_to_queue_signal.connect(self.add_run_to_queue)
        self.cg_classic.main_tab.update_run_status_signal.connect(
            self.update_run_status
        )
        self.cg_classic.queue_tab.cancel_run_signal.connect(self.cancel_run)
        self.cg_classic.queue_tab.run_priorities_updated.connect(
            self.update_run_priority
        )

        self.setCentralWidget(self.main_window)
        QShortcut(
            QKeySequence(QKeyCombination(Qt.Modifier.CTRL, Qt.Key.Key_Right)),
            self,
            self.tab_right,
        )
        QShortcut(
            QKeySequence(QKeyCombination(Qt.Modifier.CTRL, Qt.Key.Key_Left)),
            self,
            self.tab_left,
        )
        QShortcut(
            QKeySequence(QKeyCombination(Qt.Modifier.CTRL, Qt.Key.Key_Q)),
            self,
            app.quit,
        )

        self.setWindowTitle(f"Circleguard v{__version__}")
        self.setWindowIcon(QIcon(resource_path("logo/logo.ico")))
        self.start_timer()
        self.debug_window = None

        formatter = logging.Formatter(
            get_setting("log_format"), datefmt=get_setting("timestamp_format")
        )
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

        geometry = get_setting_raw("CircleguardWindow/geometry")
        if geometry:
            self.restoreGeometry(geometry)
        else:
            # if we don't know what size we were before, use 960x750
            self.resize(960, 750)

    def on_setting_changed(self, setting, new_value):
        if setting == "log_save":
            if not new_value:
                # same as disabling the handler (CRITICAL=50)
                self.file_handler.setLevel(51)
            else:
                # same as default (passes all records to the attached logger)
                self.file_handler.setLevel(logging.NOTSET)
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

    def closeEvent(self, event):
        set_setting_raw("CircleguardWindow/geometry", self.saveGeometry())

    def url_scheme_called(self, url):
        from circleguard import Circleguard, Mod, ReplayMap

        # url is bytes, so decode back to str
        url = url.decode()
        # windows appends an extra slash even if the original url didn't have
        # it, so remove it
        url = url.strip("/")
        # all urls can have any of the following parameters:
        # * m - the map id
        # * u - the first user's id
        # * u2 - the second user's id
        # * t - the timestamp to start at
        # * m1 - the mods the first replay was played with
        # * m2 - the mods the second replay was played with
        # For example, a url might look like
        # circleguard://m=221777&u=2757689&m1=HDHRu2=3219026&m2=HDHR
        map_id = int(re.compile(r"m=(.*?)(&|$)").search(url).group(1))
        user_id = int(re.compile(r"u=(.*?)(&|$)").search(url).group(1))
        timestamp_match = re.compile(r"t=(.*?)(&|$)").search(url)
        # start at the beginning if timestamp isn't specified
        timestamp = int(timestamp_match.group(1)) if timestamp_match else 0

        # mods is optional, will take the user's highest play on the map if not
        # specified
        mods1_match = re.compile(r"m1=(.*?)(&|$)").search(url)
        mods1 = None
        if mods1_match:
            mods1 = mods1_match.group(1)

        user_id_2_match = re.compile(r"u2=(.*?)(&|$)").search(url)
        user_id_2 = None
        if user_id_2_match:
            user_id_2 = int(user_id_2_match.group(1))

        mods2_match = re.compile(r"m2=(.*?)(&|$)").search(url)
        mods2 = None
        if mods2_match:
            mods2 = mods2_match.group(1)

        # convert the string into an actual mods object if we received it
        mods1 = Mod(mods1) if mods1 else None
        r = ReplayMap(map_id, user_id, mods1)
        cg = Circleguard(get_setting("api_key"))
        cg.load(r)
        replays = [r]

        if user_id_2:
            mods2 = Mod(mods2) if mods2 else None
            r2 = ReplayMap(map_id, user_id_2, mods2)
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
        check for stderr messages (because logging prints to stderr not stdout,
        and it's nice to have stdout reserved) and then print cg results.
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
        last_check = datetime.strptime(
            get_setting("last_update_check"), get_setting("timestamp_format")
        )
        next_check = last_check + timedelta(hours=1)
        if next_check > datetime.now():
            self.update_label(self.get_version_update_str())
            return
        try:
            import requests
            from requests import RequestException

            # check for new version
            git_request = requests.get(
                "https://api.github.com/repos/circleguard/circleguard/releases/latest"
            ).json()
            git_version = version.parse(git_request["name"])
            set_setting("latest_version", git_version)
            set_setting(
                "last_update_check",
                datetime.now().strftime(get_setting("timestamp_format")),
            )
        except RequestException:
            # user is probably offline
            pass
        self.update_label(self.get_version_update_str())

    def get_version_update_str(self):
        current_version = version.parse(__version__)
        if current_version < version.parse(get_setting("latest_version")):
            return "<a href='https://github.com/circleguard/circleguard/releases/latest'>Update available!</a>"
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
            r1 = result.replay1
            r2 = result.replay2
            circleguard_url = f"circleguard://m={r1.map_id}&u={r1.user_id}&m1={r1.mods.short_name()}&u2={r2.user_id}&m2={r2.mods.short_name()}"
            label_text = get_setting("string_result_steal").format(
                ts=timestamp,
                similarity=result.similarity,
                r=result,
                r1=r1,
                r2=r2,
                earlier_replay_mods_short_name=result.earlier_replay.mods.short_name(),
                earlier_replay_mods_long_name=result.earlier_replay.mods.long_name(),
                later_replay_mods_short_name=result.later_replay.mods.short_name(),
                later_replay_mods_long_name=result.later_replay.mods.long_name(),
            )
            template_text = get_setting("template_steal").format(
                ts=timestamp,
                similarity=result.similarity,
                r=result,
                r1=r1,
                r2=r2,
                earlier_replay_mods_short_name=result.earlier_replay.mods.short_name(),
                earlier_replay_mods_long_name=result.earlier_replay.mods.long_name(),
                later_replay_mods_short_name=result.later_replay.mods.short_name(),
                later_replay_mods_long_name=result.later_replay.mods.long_name(),
                circleguard_url=circleguard_url,
            )
            replays = [r1, r2]

        elif isinstance(result, RelaxResult):
            circleguard_url = f"circleguard://m={result.replay.map_id}&u={result.replay.user_id}&m1={result.replay.mods.short_name()}"
            label_text = get_setting("string_result_relax").format(
                ts=timestamp,
                ur=result.ur,
                r=result,
                replay=result.replay,
                mods_short_name=result.replay.mods.short_name(),
                mods_long_name=result.replay.mods.long_name(),
            )
            template_text = get_setting("template_relax").format(
                ts=timestamp,
                ur=result.ur,
                r=result,
                replay=result.replay,
                mods_short_name=result.replay.mods.short_name(),
                mods_long_name=result.replay.mods.long_name(),
                circleguard_url=circleguard_url,
            )
            replays = [result.replay]
        elif isinstance(result, CorrectionResult):
            circleguard_url = f"circleguard://m={result.replay.map_id}&u={result.replay.user_id}&m1={result.replay.mods.short_name()}"
            label_text = get_setting("string_result_correction").format(
                ts=timestamp,
                r=result,
                num_snaps=len(result.snaps),
                replay=result.replay,
                mods_short_name=result.replay.mods.short_name(),
                mods_long_name=result.replay.mods.long_name(),
            )

            snap_table = (
                "| Time (ms) | Angle (°) | Distance (px) |\n" "| :-: | :-: | :-: |\n"
            )
            for snap in result.snaps:
                snap_table += (
                    f"| {snap.time:.0f} | {snap.angle:.2f} | {snap.distance:.2f} |\n"
                )
            template_text = get_setting("template_correction").format(
                ts=timestamp,
                r=result,
                replay=result.replay,
                snap_table=snap_table,
                mods_short_name=result.replay.mods.short_name(),
                mods_long_name=result.replay.mods.long_name(),
                circleguard_url=circleguard_url,
            )
            replays = [result.replay]
        elif isinstance(result, TimewarpResult):
            circleguard_url = f"circleguard://m={result.replay.map_id}&u={result.replay.user_id}&m1={result.replay.mods.short_name()}"
            label_text = get_setting("string_result_timewarp").format(
                ts=timestamp,
                r=result,
                replay=result.replay,
                frametime=result.frametime,
                mods_short_name=result.replay.mods.short_name(),
                mods_long_name=result.replay.mods.long_name(),
            )
            template_text = get_setting("template_timewarp").format(
                ts=timestamp,
                r=result,
                frametime=result.frametime,
                mods_short_name=result.replay.mods.short_name(),
                mods_long_name=result.replay.mods.long_name(),
                circleguard_url=circleguard_url,
            )
            replays = [result.replay]
        elif isinstance(result, AnalysisResult):
            replays = result.replays
            # special case that occurs often, we can show more info if there's only a single replay
            if len(replays) == 1:
                r = replays[0]
                label_text = get_setting("string_result_visualization_single").format(
                    ts=timestamp,
                    replay=r,
                    mods_short_name=r.mods.short_name(),
                    mods_long_name=r.mods.long_name(),
                )
            else:
                label_text = get_setting("string_result_visualization").format(
                    ts=timestamp,
                    replay_amount=len(result.replays),
                    map_id=result.replays[0].map_id,
                )

        result_widget = ResultW(label_text, result, replays)
        # set button signal connections (visualize and copy template to clipboard)
        result_widget.visualize_button_pressed_signal.connect(
            partial(
                self.cg_classic.main_tab.visualize,
                result_widget.replays,
                result_widget.replays[0].map_id,
                result_widget.result,
            )
        )
        result_widget.template_button_pressed_signal.connect(
            partial(self.copy_to_clipboard, template_text)
        )
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

    def update_run_priority(self, run_priorities):
        self.cg_classic.main_tab.run_priorities = run_priorities

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
        cg = QPalette.ColorGroup
        cr = QPalette.ColorRole

        if theme == "dark":
            DARK_GREY = QColor(53, 53, 53)

            dark_p = self.app.style().standardPalette()

            dark_p.setColor(cg.Normal, cr.Window, DARK_GREY)
            dark_p.setColor(cg.Normal, cr.WindowText, Qt.GlobalColor.white)
            dark_p.setColor(cg.Normal, cr.Base, QColor(25, 25, 25))
            dark_p.setColor(cg.Normal, cr.AlternateBase, DARK_GREY)
            dark_p.setColor(cg.Normal, cr.ToolTipBase, DARK_GREY)
            dark_p.setColor(cg.Normal, cr.ToolTipText, Qt.GlobalColor.white)
            dark_p.setColor(cg.Normal, cr.Text, Qt.GlobalColor.white)
            dark_p.setColor(cg.Normal, cr.Button, DARK_GREY)
            dark_p.setColor(cg.Normal, cr.ButtonText, Qt.GlobalColor.white)
            dark_p.setColor(cg.Normal, cr.BrightText, Qt.GlobalColor.red)
            dark_p.setColor(cg.Normal, cr.Highlight, ACCENT_COLOR)
            dark_p.setColor(cg.Normal, cr.PlaceholderText, Qt.GlobalColor.darkGray)

            # also change for inactive (eg when app is in background)
            dark_p.setColor(cg.Inactive, cr.Window, DARK_GREY)
            dark_p.setColor(cg.Inactive, cr.WindowText, Qt.GlobalColor.white)
            dark_p.setColor(cg.Inactive, cr.Base, QColor(25, 25, 25))
            dark_p.setColor(cg.Inactive, cr.AlternateBase, DARK_GREY)
            dark_p.setColor(cg.Inactive, cr.ToolTipBase, DARK_GREY)
            dark_p.setColor(cg.Inactive, cr.ToolTipText, Qt.GlobalColor.white)
            dark_p.setColor(cg.Inactive, cr.Text, Qt.GlobalColor.white)
            dark_p.setColor(cg.Inactive, cr.Button, DARK_GREY)
            dark_p.setColor(cg.Inactive, cr.ButtonText, Qt.GlobalColor.white)
            dark_p.setColor(cg.Inactive, cr.BrightText, Qt.GlobalColor.red)
            dark_p.setColor(cg.Inactive, cr.Highlight, ACCENT_COLOR)

            dark_p.setColor(cg.Normal, cr.HighlightedText, Qt.GlobalColor.black)
            dark_p.setColor(cg.Disabled, cr.Text, Qt.GlobalColor.darkGray)
            dark_p.setColor(cg.Disabled, cr.ButtonText, Qt.GlobalColor.darkGray)
            dark_p.setColor(cg.Disabled, cr.Highlight, Qt.GlobalColor.darkGray)
            dark_p.setColor(cg.Disabled, cr.Base, DARK_GREY)
            dark_p.setColor(cg.Disabled, cr.Button, DARK_GREY)
            dark_p.setColor(cg.Normal, cr.Link, ACCENT_COLOR)
            dark_p.setColor(cg.Normal, cr.LinkVisited, ACCENT_COLOR)
            dark_p.setColor(cg.Inactive, cr.Link, ACCENT_COLOR)
            dark_p.setColor(cg.Inactive, cr.LinkVisited, ACCENT_COLOR)

            # the `bigButton` class is necessary because qt (or the fusion
            # style, not sure which) is putting a *gradient* on the buttons by
            # by default. Kind of crazy if you ask me, but it does make the
            # small buttons look good, so I only want to change it to a flat
            # color for larger buttons (and also round their corners because
            # large buttons don't look so good when they're blocky)

            # the QListWidget border removal is because it clashes with the
            # border we're drawing around our SelectableLoadables and the ui
            # looks too busy with that many borders

            # QPushButton:disabled is because the default disabled style has a
            # white border which looks terrible in dark mode

            self.app.setPalette(dark_p)
            self.app.setStyleSheet(
                """
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
                SelectableLoadable, DragWidget, ReplayMapVis {
                    border: 1.5px solid rgb(32, 32, 32);
                }
                ReplayMapCreation {
                    border: 1.5px solid #1f1f1f;
                }
                QListWidget {
                    background-color: rgb(53, 53, 53);
                    QListWidget
                }
                QPushButton:disabled {
                    border: 1px solid rgb(47, 47, 47);
                    border-radius: 3%;
                }
                """
            )
        else:
            self.app.setPalette(self.app.style().standardPalette())
            updated_palette = QPalette()
            # fixes inactive items not being greyed out
            updated_palette.setColor(
                cg.Disabled, cr.ButtonText, Qt.GlobalColor.darkGray
            )
            updated_palette.setColor(cg.Normal, cr.Highlight, ACCENT_COLOR)
            updated_palette.setColor(cg.Disabled, cr.Highlight, Qt.GlobalColor.darkGray)
            updated_palette.setColor(cg.Inactive, cr.Highlight, Qt.GlobalColor.darkGray)
            updated_palette.setColor(cg.Normal, cr.Link, ACCENT_COLOR)
            updated_palette.setColor(cg.Normal, cr.LinkVisited, ACCENT_COLOR)
            updated_palette.setColor(
                cg.Normal, cr.PlaceholderText, Qt.GlobalColor.darkGray
            )
            self.app.setPalette(updated_palette)
            self.app.setStyleSheet(
                """
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
                """
            )
