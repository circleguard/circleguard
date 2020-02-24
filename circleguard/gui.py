import os
import sys
from pathlib import Path
from multiprocessing.pool import ThreadPool
from queue import Queue, Empty
from functools import partial
import logging
import colorsys
import traceback
import threading
from datetime import datetime
import math
import time
import json

from PyQt5.QtCore import Qt, QTimer, qInstallMessageHandler, QObject, pyqtSignal, QUrl, QMimeData, QPoint
from PyQt5.QtWidgets import (QWidget, QFrame, QTabWidget, QTextEdit, QPushButton, QLabel, QScrollArea, QFrame, QProgressBar,
                             QVBoxLayout, QShortcut, QGridLayout, QApplication, QMainWindow, QSizePolicy, QComboBox)
from PyQt5.QtGui import QPalette, QColor, QIcon, QKeySequence, QTextCursor, QPainter, QDesktopServices, QDrag, QPixmap

# app needs to be initialized before settings is imported so QStandardPaths resolves
# corerctly with the applicationName
app = QApplication([])
app.setStyle("Fusion")
app.setApplicationName("Circleguard")

from circleguard import (Circleguard, set_options, Loader, NoInfoAvailableException,
                        ReplayMap, ReplayPath, User, Map, Check, MapUser, StealDetect,
                        RelaxDetect, CorrectionDetect, ReplayStealingResult, RelaxResult, CorrectionResult)
from circleguard import __version__ as cg_version

from utils import resource_path, run_update_check, Run, parse_mod_string, InvalidModException, delete_widget
from widgets import (set_event_window, InputWidget, ResetSettings, WidgetCombiner,
                     FolderChooser, IdWidgetCombined, Separator, OptionWidget, ButtonWidget,
                     LoglevelWidget, SliderBoxSetting, BeatmapTest, ResultW, LineEditSetting,
                     EntryWidget, RunWidget)

from settings import get_setting, set_setting, overwrite_config, overwrite_with_config_settings
from visualizer import VisualizerWindow
import wizard
from version import __version__


log = logging.getLogger(__name__)

# save old excepthook
sys._excepthook = sys.excepthook

def write_log(message):
    log_dir = resource_path(get_setting("log_dir"))
    if not os.path.exists(log_dir): # create dir if nonexistent
        os.makedirs(log_dir)
    directory = os.path.join(log_dir, "circleguard.log")
    with open(directory, 'a+') as f: # append so it creates a file if it doesn't exist
        f.seek(0)
        data = f.read().splitlines(True)
    data.append(message+"\n")
    with open(directory, 'w+') as f:
        f.writelines(data[-1000:]) # keep file at 1000 lines

# this allows us to log any and all exceptions thrown to a log file -
# pyqt likes to eat exceptions and quit silently
def my_excepthook(exctype, value, tb):
    # call original excepthook before ours
    write_log("sys.excepthook error\n"
              "Type: " + str(value) + "\n"
              "Value: " + str(value) + "\n"
              "Traceback: " + "".join(traceback.format_tb(tb)) + '\n')
    sys._excepthook(exctype, value, tb)

sys.excepthook = my_excepthook

# sys.excepthook doesn't persist across threads
# (http://bugs.python.org/issue1230540). This is a hacky workaround that overrides
# the threading init method to use our excepthook.
# https://stackoverflow.com/a/31622038
threading_init = threading.Thread.__init__
def init(self, *args, **kwargs):
    threading_init(self, *args, **kwargs)
    run_original = self.run

    def run_with_except_hook(*args2, **kwargs2):
        try:
            run_original(*args2, **kwargs2)
        except Exception:
            sys.excepthook(*sys.exc_info())
    self.run = run_with_except_hook
threading.Thread.__init__ = init


# logging methodology heavily adapted from https://stackoverflow.com/q/28655198/12164878
class Handler(QObject, logging.Handler):
    new_message = pyqtSignal(object)

    def __init__(self):
        super().__init__()

    def emit(self, record):
        message = self.format(record)
        self.new_message.emit(message)


class WindowWrapper(QMainWindow):
    def __init__(self, clipboard):
        super().__init__()

        self.clipboard = clipboard
        self.progressbar = QProgressBar()
        self.progressbar.setFixedWidth(250)
        self.current_state_label = QLabel("Idle")
        self.current_state_label.setTextFormat(Qt.RichText)
        self.current_state_label.setTextInteractionFlags(Qt.TextBrowserInteraction)
        self.current_state_label.setOpenExternalLinks(True)
        # statusBar() is a qt function that will create a status bar tied to the window
        # if it doesnt exist, and access the existing one if it does.
        self.statusBar().addWidget(WidgetCombiner(self.progressbar, self.current_state_label))
        self.statusBar().setSizeGripEnabled(False)
        self.statusBar().setContentsMargins(8, 2, 10, 2)

        self.main_window = MainWindow()
        self.main_window.main_tab.set_progressbar_signal.connect(self.set_progressbar)
        self.main_window.main_tab.increment_progressbar_signal.connect(self.increment_progressbar)
        self.main_window.main_tab.update_label_signal.connect(self.update_label)
        self.main_window.main_tab.add_result_signal.connect(self.add_result)
        self.main_window.main_tab.write_to_terminal_signal.connect(self.main_window.main_tab.write)
        self.main_window.main_tab.add_run_to_queue_signal.connect(self.add_run_to_queue)
        self.main_window.main_tab.update_run_status_signal.connect(self.update_run_status)
        self.main_window.queue_tab.cancel_run_signal.connect(self.cancel_run)

        self.setCentralWidget(self.main_window)
        QShortcut(QKeySequence(Qt.CTRL+Qt.Key_Right), self, self.tab_right)
        QShortcut(QKeySequence(Qt.CTRL+Qt.Key_Left), self, self.tab_left)
        QShortcut(QKeySequence(Qt.CTRL+Qt.Key_Q), self, partial(self.cancel_all_runs, self))

        self.setWindowTitle(f"Circleguard v{__version__}")
        self.setWindowIcon(QIcon(str(resource_path("resources/logo.ico"))))
        self.start_timer()
        self.debug_window = None

        handler = Handler()
        logging.getLogger("circleguard").addHandler(handler)
        logging.getLogger("ossapi").addHandler(handler)
        logging.getLogger(__name__).addHandler(handler)
        formatter = logging.Formatter("[%(levelname)s] %(asctime)s.%(msecs)04d %(message)s (%(name)s, %(filename)s:%(lineno)d)", datefmt="%Y/%m/%d %H:%M:%S")
        handler.setFormatter(formatter)
        handler.new_message.connect(self.log)

        self.thread = threading.Thread(target=self._change_label_update)
        self.thread.start()

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
        self.main_window.main_tab.check_circleguard_queue()

    def log(self, message):
        """
        Message is the string message sent to the io stream
        """

        if get_setting("log_save"):
            write_log(message)

        # TERMINAL / BOTH
        if get_setting("log_output") in [1, 3]:
            self.main_window.main_tab.write(message)

        # NEW WINDOW / BOTH
        if get_setting("log_output") in [2, 3]:
            if self.debug_window and self.debug_window.isVisible():
                self.debug_window.write(message)
            else:
                self.debug_window = DebugWindow()
                self.debug_window.show()
                self.debug_window.write(message)

    def update_label(self, text):
        self.current_state_label.setText(text)

    def _change_label_update(self):
        self.update_label(run_update_check())

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

        if type(result) is ReplayStealingResult:
            label_text = get_setting("string_result_steal").format(ts=timestamp, similarity=result.similarity, r=result, r1=result.replay1, r2=result.replay2,
                                        replay1_mods_short_name=result.replay1.mods.short_name(), replay1_mods_long_name=result.replay1.mods.long_name(),
                                        replay2_mods_short_name=result.replay2.mods.short_name(), replay2_mods_long_name=result.replay2.mods.long_name())
            template_text = get_setting("template_steal").format(ts=timestamp, similarity=result.similarity, r=result, r1=result.replay1, r2=result.replay2,
                                        replay1_mods_short_name=result.replay1.mods.short_name(), replay1_mods_long_name=result.replay1.mods.long_name(),
                                        replay2_mods_short_name=result.replay2.mods.short_name(), replay2_mods_long_name=result.replay2.mods.long_name())
            replays = [result.replay1, result.replay2]

        elif type(result) is RelaxResult:
            label_text = get_setting("string_result_relax").format(ts=timestamp, ur=result.ur, r=result,
                                        replay=result.replay, mods_short_name=result.replay.mods.short_name(),
                                        mods_long_name=result.replay.mods.long_name())
            template_text = get_setting("template_relax").format(ts=timestamp, ur=result.ur, r=result,
                                        replay=result.replay, mods_short_name=result.replay.mods.short_name(),
                                        mods_long_name=result.replay.mods.long_name())
            replays = [result.replay]
        elif type(result) is CorrectionResult:
            label_text = get_setting("string_result_correction").format(ts=timestamp, r=result, num_snaps=len(result.snaps), replay=result.replay,
                                        mods_short_name=result.replay.mods.short_name(), mods_long_name=result.replay.mods.long_name())

            snap_table = ("| Time (ms) | Angle (°) | Distance (px) |\n"
                            "| :-: | :-: | :-: |\n")
            for snap in result.snaps:
                snap_table += "| {:.0f} | {:.2f} | {:.2f} |\n".format(snap.time, snap.angle, snap.distance)
            template_text = get_setting("template_correction").format(ts=timestamp, r=result, replay=result.replay, snap_table=snap_table,
                                        mods_short_name=result.replay.mods.short_name(), mods_long_name=result.replay.mods.long_name())
            replays = [result.replay]

        result_widget = ResultW(label_text, result, replays)
        # set button signal connections (visualize and copy template to clipboard)
        result_widget.button.clicked.connect(partial(self.main_window.main_tab.visualize, result_widget.replays, result_widget.replays[0].map_id))
        result_widget.button_clipboard.clicked.connect(partial(self.copy_to_clipboard, template_text))
        # remove info text if shown
        if not self.main_window.results_tab.results.info_label.isHidden():
            self.main_window.results_tab.results.info_label.hide()
        self.main_window.results_tab.results.layout.insertWidget(0,result_widget)

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
        """Called when the app.aboutToQuit signal is emitted"""
        if self.debug_window is not None:
            self.debug_window.close()
        if self.main_window.main_tab.visualizer_window is not None:
            self.main_window.main_tab.visualizer_window.close()
        overwrite_config()


class DebugWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Debug Output")
        self.setWindowIcon(QIcon(str(resource_path("resources/logo.ico"))))
        terminal = QTextEdit(self)
        terminal.setReadOnly(True)
        terminal.ensureCursorVisible()
        self.terminal = terminal
        self.setCentralWidget(self.terminal)
        self.resize(800, 350)

    def write(self, message):
        self.terminal.append(message)

class MainWindow(QFrame):
    def __init__(self):
        super().__init__()

        self.tabs = QTabWidget()
        self.main_tab = MainTab()
        self.results_tab = ResultsTab()
        self.queue_tab = QueueTab()
        self.thresholds_tab = ThresholdsTab()
        self.settings_tab = SettingsTab()
        self.tabs.addTab(self.main_tab, "Main")
        self.tabs.addTab(self.results_tab, "Results")
        self.tabs.addTab(self.queue_tab, "Queue")
        self.tabs.addTab(self.thresholds_tab, "Thresholds")
        self.tabs.addTab(self.settings_tab, "Settings")
        # so when we switch from settings tab to main tab, whatever tab we're on gets changed if we delete our api key
        self.tabs.currentChanged.connect(self.main_tab.check_run_button)

        self.layout = QVBoxLayout()
        self.layout.addWidget(self.tabs)
        self.layout.setContentsMargins(10, 10, 10, 0)
        self.setLayout(self.layout)


class MainTab(QFrame):
    set_progressbar_signal = pyqtSignal(int) # max progress
    increment_progressbar_signal = pyqtSignal(int) # increment value
    update_label_signal = pyqtSignal(str)
    write_to_terminal_signal = pyqtSignal(str)
    add_result_signal = pyqtSignal(object) # Result
    add_run_to_queue_signal = pyqtSignal(object) # Run object (or a subclass)
    update_run_status_signal = pyqtSignal(int, str) # run_id, status_str
    print_results_signal = pyqtSignal() # called after a run finishes to flush the results queue before printing "Done"

    LOADABLES_COMBOBOX_REGISTRY = ["Map Replay", "Local Replay", "Map", "User", "All Map Replays by User"]
    CHECKS_COMBOBOX_REGISTRY = ["Replay Stealing/Remodding", "Relax", "Aim Correction"]

    def __init__(self):
        super().__init__()

        self.loadables_combobox = QComboBox(self)
        self.loadables_combobox.setInsertPolicy(QComboBox.NoInsert)
        for loadable in MainTab.LOADABLES_COMBOBOX_REGISTRY:
            self.loadables_combobox.addItem(loadable, loadable)
        self.loadables_button = QPushButton("Add", self)
        self.loadables_button.clicked.connect(self.add_loadable)

        self.checks_combobox = QComboBox(self)
        self.checks_combobox.setInsertPolicy(QComboBox.NoInsert)
        for check in MainTab.CHECKS_COMBOBOX_REGISTRY:
            self.checks_combobox.addItem(check, check)
        self.checks_button = QPushButton("Add", self)
        self.checks_button.clicked.connect(self.add_check)

        self.loadables_scrollarea = QScrollArea(self)
        self.loadables_scrollarea.setWidget(ScrollableLoadablesWidget())
        self.loadables_scrollarea.setWidgetResizable(True)

        self.checks_scrollarea = QScrollArea(self)
        self.checks_scrollarea.setWidget(ScrollableChecksWidget())
        self.checks_scrollarea.setWidgetResizable(True)

        self.loadables = [] # for deleting later
        self.checks = [] # for deleting later

        self.print_results_signal.connect(self.print_results)

        self.q = Queue()
        self.cg_q = Queue()
        self.helper_thread_running = False
        self.runs = [] # Run objects for canceling runs
        self.run_id = 0
        self.visualizer_window = None

        terminal = QTextEdit(self)
        terminal.setFocusPolicy(Qt.ClickFocus)
        terminal.setReadOnly(True)
        terminal.ensureCursorVisible()
        self.terminal = terminal

        self.run_button = QPushButton()
        self.run_button.setText("Run")
        self.run_button.clicked.connect(self.add_circleguard_run)

        layout = QGridLayout()
        layout.addWidget(self.loadables_combobox, 0, 0, 1, 7)
        layout.addWidget(self.loadables_button, 0, 7, 1, 1)
        layout.addWidget(self.checks_combobox, 0, 8, 1, 7)
        layout.addWidget(self.checks_button, 0, 15, 1, 1)
        layout.addWidget(self.loadables_scrollarea, 1, 0, 4, 8)
        layout.addWidget(self.checks_scrollarea, 1, 8, 4, 8)
        layout.addWidget(self.terminal, 5, 0, 2, 16)
        layout.addWidget(self.run_button, 7, 0, 1, 16)

        self.setLayout(layout)
        self.check_run_button() # disable run button if there is no api key

    # am well aware that there's much duplicated code between remove_loadable,
    # remove_check, add_loadable, and add_check. Don't feel like writing
    # more generic functions for them right now.
    def remove_loadable(self, loadable_id):
        # should only ever be one occurence, a comp + index works well enough
        loadables = [l for l in self.loadables if l.loadable_id == loadable_id]
        if not loadables: # sometimes an empty list, I don't know how if you need a loadable to click the delete button...
            return
        loadable = loadables[0]
        self.loadables_scrollarea.widget().layout.removeWidget(loadable)
        delete_widget(loadable)
        self.loadables.remove(loadable)
        # remove deleted loadables from Checks as well
        for check in self.checks:
            check.remove_loadable(loadable_id)

    def remove_check(self, check_id):
        # see above method for comments
        checks = [c for c in self.checks if c.check_id == check_id]
        if not checks:
            return
        check = checks[0]
        self.checks_scrollarea.widget().layout.removeWidget(check)
        delete_widget(check)
        self.checks.remove(check)

    def add_loadable(self):
        button_data = self.loadables_combobox.currentData()
        if button_data == "Map Replay":
            w = ReplayMapW()
        if button_data == "Local Replay":
            w = ReplayPathW()
        if button_data == "Map":
            w = MapW()
        if button_data == "User":
            w = UserW()
        if button_data == "All Map Replays by User":
            w = MapUserW()
        w.remove_loadable_signal.connect(self.remove_loadable)
        self.loadables_scrollarea.widget().layout.addWidget(w)
        self.loadables.append(w)

    def add_check(self):
        button_data = self.checks_combobox.currentData()
        if button_data == "Replay Stealing/Remodding":
            w = StealCheckW()
        if button_data == "Relax":
            w = RelaxCheckW()
        if button_data == "Aim Correction":
            w = CorrectionCheckW()
        w.remove_check_signal.connect(self.remove_check)
        self.checks_scrollarea.widget().layout.addWidget(w)
        self.checks.append(w)

    def write(self, message):
        self.terminal.append(str(message).strip())
        self.scroll_to_bottom()

    def scroll_to_bottom(self):
        cursor = QTextCursor(self.terminal.document())
        cursor.movePosition(QTextCursor.End)
        self.terminal.setTextCursor(cursor)

    def add_circleguard_run(self):
        checks = self.checks
        if not checks:
            return
        for check in checks:
            # all loadable objects in this check
            # (the check only stores the loadable ids, not the objects themselves)
            # TODO
            # this is a ridiculous way to do it, but the alternative would involve serializing
            # the class into a QByteArray and passing it through the QMimeData of the QDrag,
            # then converting it back to a class on the other side, so we'll stick with this for now.

            # aka ``isinstance(check, StealCheckW)``
            if check.double_drop_area:
                loadables1 = [l for l in self.loadables if l.loadable_id in check.drop_area1.loadable_ids]
                loadables2 = [l for l in self.loadables if l.loadable_id in check.drop_area2.loadable_ids]
                check.loadables1 = loadables1
                check.loadables2 = loadables2
            else:
                loadables = [l for l in self.loadables if l.loadable_id in check.all_loadable_ids()]
                check.loadables = loadables

        # would use any() but it short circuts and doesn't call on all loadables
        all_filled = True
        for check in checks:
            for loadable in check.all_loadables():
                # don't assign to all_filled if all_filled is already False
                all_filled = loadable.check_required_fields() if all_filled else all_filled

        if not all_filled:
            # no more feedback necessary like printing to console (probably)
            # because the check_required_fields method already highlights
            # empty QLineEdits in red
            return
        checks = [check for check in checks if check.all_loadables()]
        if not checks:
            # loadables haven't been dragged to any of the checks, just return
            # so we don't have prints to the console for no reason
            return

        run = Run(checks, self.run_id, threading.Event())
        self.runs.append(run)
        self.add_run_to_queue_signal.emit(run)
        self.cg_q.put(run)
        self.run_id += 1

        # called every 1/4 seconds by timer, but force a recheck to not wait for that delay
        self.check_circleguard_queue()

    def check_run_button(self):
        # this line causes a "QObject::startTimer: Timers cannot be started from another thread" print
        # statement even though no timer interaction is going on; not sure why it happens but it doesn't
        # impact functionality. Still might be worth looking into
        self.run_button.setEnabled(False if get_setting("api_key") == "" else True)


    def check_circleguard_queue(self):
        def _check_circleguard_queue(self):
            try:
                while True:
                    run = self.cg_q.get_nowait()
                    # occurs if run is canceled before being started, it will still stop
                    # before actually loading anything but we don't want the labels to flicker
                    if run.event.wait(0):
                        continue
                    thread = threading.Thread(target=self.run_circleguard, args=[run])
                    self.helper_thread_running = True
                    thread.start()
                    # run sequentially to not confuse user with terminal output
                    thread.join()
            except Empty:
                self.helper_thread_running = False
                return

        # don't launch another thread running cg if one is already running,
        # or else multiple runs will occur at once (defeats the whole purpose
        # of sequential runs)
        if not self.helper_thread_running:
            # have to do a double thread use if we start the threads in
            # the main thread and .join, it will block the gui thread (very bad).
            thread = threading.Thread(target=_check_circleguard_queue, args=[self])
            thread.start()



    def run_circleguard(self, run):
        self.update_label_signal.emit("Loading Replays")
        self.update_run_status_signal.emit(run.run_id, "Loading Replays")
        event = run.event
        try:
            core_cache = get_setting("cache_dir") + "circleguard.db"
            slider_cache = get_setting("cache_dir")
            should_cache = get_setting("caching")
            cg = Circleguard(get_setting("api_key"), core_cache, slider_dir=slider_cache, cache=should_cache, loader=TrackerLoader)
            def _ratelimited(length):
                message = get_setting("message_ratelimited")
                ts = datetime.now()
                self.write_to_terminal_signal.emit(message.format(s=length, ts=ts))
                self.update_label_signal.emit("Ratelimited")
                self.update_run_status_signal.emit(run.run_id, "Ratelimited")
            def _check_event(event):
                """
                Checks the given event to see if it is set. If it is, the run has been canceled
                through the queue tab or by the application being quit, and this thread exits
                through sys.exit(0). If the event is not set, returns silently.
                """
                if event.wait(0):
                    self.update_label_signal.emit("Canceled")
                    self.set_progressbar_signal.emit(-1)
                    # may seem dirty, but actually relatively clean since it only affects this thread.
                    # Any cleanup we may want to do later can occur here as well
                    sys.exit(0)

            cg.loader.ratelimit_signal.connect(_ratelimited)
            cg.loader.check_stopped_signal.connect(partial(_check_event, event))

            # aggreagte loadables from all of the checks so we don't create
            # separate instances per check and double load the (otherwise)
            # identical loadable

            # discard duplicate loadableWs
            loadableWs = {loadableW for checkW in run.checks for loadableW in checkW.all_loadables()}
            # mapping of loadableW id to loadable object so each check can
            # replace its loadableWs with the same loadable object and avoid
            # double loading
            loadableW_id_to_loadable = {}

            for loadableW in loadableWs:
                loadable = None
                try:
                    if type(loadableW) is ReplayPathW:
                        loadable = ReplayPath(loadableW.path_input.path)
                    if type(loadableW) is ReplayMapW:
                        loadable = ReplayMap(int(loadableW.map_id_input.field.text()), int(loadableW.user_id_input.field.text()),
                                             mods=parse_mod_string(loadableW.mods_input.field.text()))
                    if type(loadableW) is MapW:
                        # use placeholder text (1-50) if the user inputted span is empty
                        span = loadableW.span_input.field.text() or loadableW.span_input.field.placeholderText()
                        loadable = Map(int(loadableW.map_id_input.field.text()), span=span,
                                             mods=parse_mod_string(loadableW.mods_input.field.text()))
                    if type(loadableW) is UserW:
                        loadable = User(int(loadableW.user_id_input.field.text()), span=loadableW.span_input.field.text(),
                                             mods=parse_mod_string(loadableW.mods_input.field.text()))
                    if type(loadableW) is MapUserW:
                        loadable = MapUser(int(loadableW.map_id_input.field.text()), int(loadableW.user_id_input.field.text()),
                                           span=loadableW.span_input.field.text())
                    loadableW_id_to_loadable[loadableW.loadable_id] = loadable
                except InvalidModException as e:
                    self.write_to_terminal_signal.emit(str(e))
                    self.update_label_signal.emit("Invalid arguments")
                    self.update_run_status_signal.emit(run.run_id, "Invalid arguments")
                    self.set_progressbar_signal.emit(-1)
                    sys.exit(0)

            for checkW in run.checks:
                d = None
                check_type = None
                if type(checkW) is StealCheckW:
                    steal_thresh = get_setting("steal_max_sim")
                    d = StealDetect(steal_thresh)
                    check_type = "Steal"
                if type(checkW) is RelaxCheckW:
                    relax_thresh = get_setting("relax_max_ur")
                    check_type = "Relax"
                    d = RelaxDetect(relax_thresh)
                if type(checkW) is CorrectionCheckW:
                    max_angle = get_setting("correction_max_angle")
                    min_distance = get_setting("correction_min_distance")
                    d = CorrectionDetect(max_angle, min_distance)
                    check_type = "Aim Correction"
                # retrieve loadable objects from loadableW ids
                if isinstance(checkW, StealCheckW):
                    loadables1 = [loadableW_id_to_loadable[loadableW.loadable_id] for loadableW in checkW.loadables1]
                    loadables2 = [loadableW_id_to_loadable[loadableW.loadable_id] for loadableW in checkW.loadables2]
                    c = Check(loadables1, loadables2=loadables2, detect=d)
                else:
                    loadables = [loadableW_id_to_loadable[loadableW.loadable_id] for loadableW in checkW.loadables]
                    c = Check(loadables, detect=d)
                message_loading_info = get_setting("message_loading_info").format(ts=datetime.now(), check_type=check_type)
                self.write_to_terminal_signal.emit(message_loading_info)
                cg.load_info(c)
                replays = c.all_replays() + c.all_replays2()
                # don't show "loading 2 replays" if they were already loaded
                # by a previous check, would be misleading
                num_unloaded = 0
                num_total = c.num_replays()
                for r in replays:
                    if not r.loaded:
                        num_unloaded += 1
                if num_unloaded != 0:
                    self.set_progressbar_signal.emit(num_unloaded)
                else:
                    self.set_progressbar_signal.emit(1)
                num_loaded = num_total - num_unloaded
                message_loading_replays = get_setting("message_loading_replays").format(ts=datetime.now(),
                                num_total=num_total, num_previously_loaded=num_loaded, num_unloaded=num_unloaded,
                                check_type=check_type)
                self.write_to_terminal_signal.emit(message_loading_replays)
                for replay in replays:
                    _check_event(event)
                    cg.load(replay)
                    self.increment_progressbar_signal.emit(1)
                c.loaded = True
                # change progressbar into an undetermined state (animation with
                # stripes sliding horizontally) to indicate we're processing
                # the data
                self.set_progressbar_signal.emit(0)
                message_starting_investigation = get_setting("message_starting_investigation").format(ts=datetime.now(),
                                num_total=num_total, num_previously_loaded=num_loaded, num_unloaded=num_unloaded,
                                check_type=check_type)
                self.write_to_terminal_signal.emit(message_starting_investigation)
                self.update_label_signal.emit("Investigating Replays")
                self.update_run_status_signal.emit(run.run_id, "Investigating Replays")
                for result in cg.run(c):
                    _check_event(event)
                    self.q.put(result)
                self.print_results_signal.emit() # flush self.q

            self.set_progressbar_signal.emit(-1) # empty progressbar
            # 'flush' self.q so there's no more results left and message_finished_investigation
            # won't print before results from that investigation which looks strange.
            # Signal instead of call to be threadsafe and avoid
            # ```
            # QObject::connect: Cannot queue arguments of type 'QTextCursor'
            # (Make sure 'QTextCursor' is registered using qRegisterMetaType().)
            # ```
            # warning
            self.print_results_signal.emit()
            self.write_to_terminal_signal.emit(get_setting("message_finished_investigation").format(ts=datetime.now()))

        except NoInfoAvailableException:
            self.write_to_terminal_signal.emit("No information found for those arguments. Please check your inputs and make sure the given user/map exists")
            self.set_progressbar_signal.emit(-1)

        except Exception:
            log.exception("Error while running circlecore. Please "
                          "report this to the developers through discord or github.\n")

        self.update_label_signal.emit("Idle")
        self.update_run_status_signal.emit(run.run_id, "Finished")

    def print_results(self):
        try:
            while True:
                result = self.q.get_nowait()
                ts = datetime.now() # ts = timestamp
                message = None
                if type(result) is ReplayStealingResult:
                    if result.ischeat:
                        message = get_setting("message_steal_found").format(ts=ts, sim=result.similarity, r=result, replay1=result.replay1, replay2=result.replay2,
                                                replay1_mods_short_name=result.replay1.mods.short_name(), replay1_mods_long_name=result.replay1.mods.long_name(),
                                                replay2_mods_short_name=result.replay2.mods.short_name(), replay2_mods_long_name=result.replay2.mods.long_name())
                    elif result.similarity < get_setting("steal_max_sim_display"):
                        message = get_setting("message_steal_found_display").format(ts=ts, sim=result.similarity, r=result, replay1=result.replay1,
                                                replay2=result.replay2, replay1_mods_short_name=result.replay1.mods.short_name(), replay1_mods_long_name=result.replay1.mods.long_name(),
                                                replay2_mods_short_name=result.replay2.mods.short_name(), replay2_mods_long_name=result.replay2.mods.long_name())

                if type(result) is RelaxResult:
                    if result.ischeat:
                        message = get_setting("message_relax_found").format(ts=ts, r=result, replay=result.replay, ur=result.ur,
                                                mods_short_name=result.replay.mods.short_name(), mods_long_name=result.replay.mods.long_name())
                    elif result.ur < get_setting("relax_max_ur_display"):
                        message = get_setting("message_relax_found_display").format(ts=ts, r=result, replay=result.replay, ur=result.ur,
                                                mods_short_name=result.replay.mods.short_name(), mods_long_name=result.replay.mods.long_name())

                if type(result) is CorrectionResult:
                    if result.ischeat:
                        snap_message = get_setting("message_correction_snaps")
                        snap_text = "\n".join([snap_message.format(time=snap.time, angle=snap.angle, distance=snap.distance) for snap in result.snaps])
                        message = get_setting("message_correction_found").format(ts=ts, r=result, replay=result.replay, snaps=snap_text,
                                                mods_short_name=result.replay.mods.short_name(), mods_long_name=result.replay.mods.long_name())
                # message is None if the result isn't a cheat and doesn't
                # satisfy its display threshold
                if message:
                    self.write(message)
                if result.ischeat:
                    QApplication.beep()
                    QApplication.alert(self)
                    # add to Results Tab so it can be played back on demand
                    self.add_result_signal.emit(result)

        except Empty:
            pass

    def visualize(self, replays, beatmap_id=None):
        self.visualizer_window = VisualizerWindow(replays=replays, beatmap_id=beatmap_id)
        self.visualizer_window.show()


class TrackerLoader(Loader, QObject):
    """
    A circleguard.Loader subclass that emits a signal when the loader is ratelimited.
    It inherits from QObject to allow us to use qt signals.
    """
    ratelimit_signal = pyqtSignal(int) # length of the ratelimit in seconds
    check_stopped_signal = pyqtSignal()
    # how often to emit check_stopped_signal when ratelimited, in seconds
    INTERVAL = 0.250

    def __init__(self, key, cacher=None):
        Loader.__init__(self, key, cacher)
        QObject.__init__(self)

    def _ratelimit(self, length):
        self.ratelimit_signal.emit(length)
        # how many times to wait for 1/4 second (rng standing for range)
        # we do this loop in order to tell run_circleguard to check if the run
        # was canceled, or the application quit, instead of hanging on a long
        # time.sleep
        rng = math.ceil(length / self.INTERVAL)
        for _ in range(rng):
            time.sleep(self.INTERVAL)
            self.check_stopped_signal.emit()


class VisualizeTab(QFrame):
    def __init__(self):
        super().__init__()
        self.result_frame = ResultsTab()
        self.result_frame.results.info_label.hide()
        self.map_id = None
        self.q = Queue()
        self.replays = []
        cache_path = resource_path(get_setting("cache_dir") + "circleguard.db")
        self.cg = Circleguard(get_setting("api_key"), cache_path)
        self.info = QLabel(self)
        self.info.setText("Visualizes Replays. Has theoretically support for an arbitrary amount of replays.")
        self.label_map_id = QLabel(self)
        self.update_map_id_label()
        self.file_chooser = FolderChooser("Add Replays", folder_mode=False, multiple_files=True,
                                            file_ending="osu! Replayfile (*osr)", display_path=False)
        self.file_chooser.path_signal.connect(self.add_files)
        self.folder_chooser = FolderChooser("Add Folder", display_path=False)
        self.folder_chooser.path_signal.connect(self.add_folder)
        layout = QGridLayout()
        layout.addWidget(self.info)
        layout.addWidget(self.file_chooser)
        layout.addWidget(self.folder_chooser)
        layout.addWidget(self.label_map_id)
        layout.addWidget(self.result_frame)

        self.setLayout(layout)

    def start_timer(self):
        timer = QTimer(self)
        timer.timeout.connect(self.run_timer)
        timer.start(250)

    def run_timer(self):
        self.add_widget()

    def update_map_id_label(self):
        self.label_map_id.setText(f"Current beatmap_id: {self.map_id}")

    def add_files(self, paths):
        thread = threading.Thread(target=self._parse_replays, args=[paths])
        thread.start()
        self.start_timer()

    def add_folder(self, path):
        thread = threading.Thread(target=self._parse_folder, args=[path])
        thread.start()
        self.start_timer()

    def _parse_replays(self, paths):
        for path in paths:
            # guaranteed to end in .osr by our filter
            self._parse_replay(path)

    def _parse_folder(self, path):
        for f in os.listdir(path): # os.walk seems unnecessary
            if f.endswith(".osr"):
                self._parse_replay(os.path.join(path, f))

    def _parse_replay(self, path):
        replay = ReplayPath(path)
        self.cg.load(replay)
        if self.map_id is None or len(self.replays) == 0: # store map_id if nothing stored
            log.info(f"Changing map_id from {self.map_id} to {replay.map_id}")
            self.map_id = replay.map_id
            self.update_map_id_label()
        elif replay.map_id != self.map_id: # ignore replay with diffrent map_ids
            log.error(f"replay {replay} doesn't match with current map_id ({replay.map_id} != {self.map_id})")
            return
        if not any(replay.replay_id == r.data.replay_id for r in self.replays): # check if already stored
            log.info(f"adding new replay {replay} with replay id {replay.replay_id} on map {replay.map_id}")
            self.q.put(replay)
        else:
            log.info(f"skipping replay {replay} with replay id {replay.replay_id} on map {replay.map_id} since it's already saved")

    def add_widget(self):
        try:
            while True:
                replay = self.q.get(block=False)
                widget = EntryWidget(f"{replay.username}'s play with the id {replay.replay_id}", "Delete", replay)
                widget.clicked_signal.connect(self.remove_replay)
                self.replays.append(widget)
                self.result_frame.results.layout.insertWidget(0,widget)
        except Empty:
            pass

    def remove_replay(self, data):
        replay_ids = [replay.data.replay_id for replay in self.replays]
        index = replay_ids.index(data.replay_id)
        self.result_frame.results.layout.removeWidget(self.replays[index])
        self.replays[index].deleteLater()
        self.replays[index] = None
        self.replays.pop(index)


class SettingsTab(QFrame):
    def __init__(self):
        super().__init__()
        self.qscrollarea = QScrollArea(self)
        self.qscrollarea.setWidget(ScrollableSettingsWidget())
        self.qscrollarea.setAlignment(Qt.AlignCenter)
        self.qscrollarea.setWidgetResizable(True)

        self.info = QLabel(self)
        self.info.setText(f"Frontend v{__version__}<br/>"
                          f"Backend v{cg_version}<br/>"
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

        self.apikey_widget = LineEditSetting("Api Key", "", "password", "api_key")
        self.darkmode = OptionWidget("Dark mode", "Come join the dark side", "dark_theme")
        self.darkmode.box.stateChanged.connect(self.reload_theme)
        self.visualizer_info = OptionWidget("Show Visualizer info", "", "visualizer_info")
        self.visualizer_bg = OptionWidget("Black Visualizer bg", "Reopen Visualizer for it to apply", "visualizer_black_bg")
        self.visualizer_frametime = OptionWidget("Show frametime graph in visualizer", "", "visualizer_frametime")
        self.visualizer_bg.box.stateChanged.connect(self.reload_theme)
        self.visualizer_beatmap = OptionWidget("Render Hitobjects", "Reopen Visualizer for it to apply", "render_beatmap")
        self.cache = OptionWidget("Caching", "Downloaded replays will be cached locally", "caching")
        self.cache_location = FolderChooser("Cache Location", get_setting("cache_dir"), folder_mode=True)
        self.cache_location.path_signal.connect(partial(set_setting, "cache_dir"))
        self.cache.box.stateChanged.connect(self.cache_location.switch_enabled)

        self.open_settings = ButtonWidget("Edit Settings File", "Open", "")
        self.open_settings.button.clicked.connect(self._open_settings)

        self.sync_settings = ButtonWidget("Sync Settings", "Sync", "")
        self.sync_settings.button.clicked.connect(self._sync_settings)

        self.loglevel = LoglevelWidget("")
        self.loglevel.level_combobox.currentIndexChanged.connect(self.set_loglevel)
        self.set_loglevel() # set the default loglevel in cg, not just in gui

        self.rainbow = OptionWidget("Rainbow mode", "This is an experimental function, it may cause unintended behavior!", "rainbow_accent")
        self.rainbow.box.stateChanged.connect(self.switch_rainbow)

        self.wizard = ButtonWidget("Run Wizard", "Run", "")
        self.wizard.button.clicked.connect(self.show_wizard)

        self.layout = QVBoxLayout()
        self.layout.addWidget(Separator("General"))
        self.layout.addWidget(self.apikey_widget)
        self.layout.addWidget(self.cache)
        self.layout.addWidget(self.cache_location)
        self.layout.addWidget(self.open_settings)
        self.layout.addWidget(self.sync_settings)
        self.layout.addWidget(Separator("Appearance"))
        self.layout.addWidget(self.darkmode)
        self.layout.addWidget(self.visualizer_info)
        self.layout.addWidget(self.visualizer_frametime)
        self.layout.addWidget(self.visualizer_bg)
        self.layout.addWidget(self.visualizer_beatmap)
        self.layout.addWidget(Separator("Debug"))
        self.layout.addWidget(self.loglevel)
        self.layout.addWidget(ResetSettings())
        self.layout.addWidget(Separator("Dev"))
        self.layout.addWidget(self.rainbow)
        self.layout.addWidget(self.wizard)
        self.layout.addWidget(BeatmapTest())

        self.setLayout(self.layout)

        self.cache_location.switch_enabled(get_setting("caching"))
        # we never actually set the theme to dark anywhere
        # (even if the setting is true), it should really be
        # in the main application but uh this works too
        self.reload_theme()

    def set_loglevel(self):
        for logger in logging.root.manager.loggerDict:
            logging.getLogger(logger).setLevel(self.loglevel.level_combobox.currentData())

    def next_color(self):
        (r, g, b) = colorsys.hsv_to_rgb(self._rainbow_counter, 1.0, 1.0)
        color = QColor(int(255 * r), int(255 * g), int(255 * b))
        switch_theme(get_setting("dark_theme"), color)
        self._rainbow_counter += self._rainbow_speed
        if self._rainbow_counter >= 1:
            self._rainbow_counter = 0

    def switch_rainbow(self, state):
        set_setting("rainbow_accent", 1 if state else 0)
        if get_setting("rainbow_accent"):
            self.timer.start(1000/15)
        else:
            self.timer.stop()
            switch_theme(get_setting("dark_theme"))

    def show_wizard(self):
        self.welcome.show()

    def reload_theme(self):
        switch_theme(get_setting("dark_theme"))

    def _open_settings(self):
        overwrite_config() # generate file with latest changes
        QDesktopServices.openUrl(QUrl.fromLocalFile(get_setting("config_location")))

    def _sync_settings(self):
        overwrite_with_config_settings()


class ResultsTab(QFrame):
    def __init__(self):
        super().__init__()

        layout = QVBoxLayout()
        self.qscrollarea = QScrollArea(self)
        self.results = ResultsFrame()
        self.qscrollarea.setWidget(self.results)
        self.qscrollarea.setWidgetResizable(True)
        layout.addWidget(self.qscrollarea)
        self.setLayout(layout)


class ResultsFrame(QFrame):
    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout()
        # we want widgets to fill from top down,
        # being vertically centered looks weird
        self.layout.setAlignment(Qt.AlignTop)
        self.info_label = QLabel("After running checks, this tab will fill up "
                                 "with replays that can be played back. Newest "
                                 "results appear at the top.")
        self.layout.addWidget(self.info_label)
        self.setLayout(self.layout)


class QueueTab(QFrame):
    cancel_run_signal = pyqtSignal(int) # run_id

    def __init__(self):
        super().__init__()

        self.run_widgets = []
        layout = QVBoxLayout()
        self.qscrollarea = QScrollArea(self)
        self.queue = QueueFrame()
        self.qscrollarea.setWidget(self.queue)
        self.qscrollarea.setWidgetResizable(True)
        layout.addWidget(self.qscrollarea)
        self.setLayout(layout)

    def add_run(self, run):
        run_w = RunWidget(run)
        run_w.button.clicked.connect(partial(self.cancel_run, run.run_id))
        self.run_widgets.append(run_w)
        self.queue.layout.addWidget(run_w)

    def update_status(self, run_id, status):
        self.run_widgets[run_id].update_status(status)

    def cancel_run(self, run_id):
        self.cancel_run_signal.emit(run_id)
        self.run_widgets[run_id].cancel()

class QueueFrame(QFrame):

    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout()
        self.layout.setAlignment(Qt.AlignTop)
        self.setLayout(self.layout)

class ThresholdsTab(QFrame):
    def __init__(self):
        super().__init__()
        self.qscrollarea = QScrollArea(self)
        self.qscrollarea.setWidget(ScrollableThresholdsWidget())
        self.qscrollarea.setWidgetResizable(True)

        self.layout = QVBoxLayout()
        self.layout.addWidget(self.qscrollarea)
        self.setLayout(self.layout)

class ScrollableThresholdsWidget(QFrame):
    def __init__(self):
        super().__init__()
        self.steal_max_sim = SliderBoxSetting("Max similarity", "ReplaySteal comparisons that score below this "
                "will be stored so you can view them, and printed to the console", "steal_max_sim", 100)
        self.steal_max_sim_display = SliderBoxSetting("Max similarity display", "ReplaySteal comparisons that "
                "score below this will be printed to the console", "steal_max_sim_display", 100)
        self.relax_max_ur = SliderBoxSetting("Max ur", "Replays that have a ur lower than this will be stored "
                "so you can view them, and printed to the console", "relax_max_ur", 300)
        self.relax_max_ur_display = SliderBoxSetting("Max ur display", "Replays with a ur lower than this "
                "will be printed to the console", "relax_max_ur_display", 300)
        # display options for correction are more confusing than they're worth,
        # especially when we don't have a good mechanism for storing Snaps in
        # the Result tab or visualizer support for the Snap timestamps. TODO
        # potentially add back if we can provide good support for them.
        self.correction_max_angle = SliderBoxSetting("Max angle", "Replays with a set of three points "
                "making an angle less than this (*and* also satisfying correction_min_distance) will be stored so "
                "you can view them, and printed to the console.", "correction_max_angle", 360)
        self.correction_min_distance = SliderBoxSetting("Min distance", "Replays with a set of three points "
                "where either the distance from AB or BC is greater than this (*and* also satisfying correction_max_angle) "
                "will be stored so you can view them, and printed to the console.", "correction_min_distance", 100)

        self.layout = QVBoxLayout()
        self.layout.addWidget(Separator("Replay Stealing"))
        self.layout.addWidget(self.steal_max_sim)
        self.layout.addWidget(self.steal_max_sim_display)
        self.layout.addWidget(Separator("Relax"))
        self.layout.addWidget(self.relax_max_ur)
        self.layout.addWidget(self.relax_max_ur_display)
        self.layout.addWidget(Separator("Aim Correction"))
        self.layout.addWidget(self.correction_max_angle)
        self.layout.addWidget(self.correction_min_distance)

        self.layout.setAlignment(Qt.AlignTop)
        self.setLayout(self.layout)

def switch_theme(dark, accent=QColor(71, 174, 247)):
    set_setting("dark_theme", dark)
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
        app.setStyleSheet("""
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
        app.setStyleSheet("""
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


if __name__ == "__main__":
    # app is initialized at the top of the file
    WINDOW = WindowWrapper(app.clipboard())
    set_event_window(WINDOW)
    WINDOW.resize(900, 750)
    WINDOW.show()
    if not get_setting("ran"):
        welcome = wizard.WelcomeWindow()
        welcome.show()
        set_setting("ran", True)

    app.lastWindowClosed.connect(WINDOW.cancel_all_runs)
    app.aboutToQuit.connect(WINDOW.on_application_quit)
    app.exec_()
