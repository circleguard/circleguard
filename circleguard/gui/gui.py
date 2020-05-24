import os
import sys
from pathlib import Path
from queue import Queue, Empty
from functools import partial
import logging
from logging.handlers import RotatingFileHandler
import threading
from datetime import datetime
import math
import time

# TODO this might cause a performance hit (we only import * for convenience),
# investigate
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *

from circleguard import (Circleguard, set_options, Loader, NoInfoAvailableException,
                        ReplayMap, ReplayPath, User, Map, Check, MapUser,
                        StealResult, RelaxResult, CorrectionResult, Detect, Mod)
from circleguard import __version__ as cg_version
from circleguard.loadable import Loadable
from circlevis import BeatmapInfo
from slider import Library

from utils import resource_path, run_update_check, Run, delete_widget
from widgets import (InputWidget, ResetSettings, WidgetCombiner,
                     FolderChooser, Separator, OptionWidget, ButtonWidget,
                     LoglevelWidget, SliderBoxSetting, BeatmapTest, ResultW, LineEditSetting,
                     EntryWidget, RunWidget, ScrollableLoadablesWidget, ScrollableChecksWidget,
                     ReplayMapW, ReplayPathW, MapW, UserW, MapUserW, StealCheckW, RelaxCheckW,
                     CorrectionCheckW, VisualizerW)

from settings import get_setting, set_setting, overwrite_config, overwrite_with_config_settings, LinkableSetting, SingleLinkableSetting
from .visualizer import CGVisualizer
from wizard import CircleguardWizard
from version import __version__


log = logging.getLogger(__name__)


class DebugWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Debug Output")
        self.setWindowIcon(QIcon(resource_path("logo/logo.ico")))
        terminal = QTextEdit(self)
        terminal.setReadOnly(True)
        terminal.ensureCursorVisible()
        self.terminal = terminal
        self.setCentralWidget(self.terminal)
        self.resize(800, 350)

    def write(self, message):
        self.terminal.append(message)

class MainWindow(QFrame):
    def __init__(self, parent):
        super().__init__(parent)

        self.tabs = QTabWidget()
        self.main_tab = MainTab()
        self.results_tab = ResultsTab()
        self.queue_tab = QueueTab()
        self.thresholds_tab = ThresholdsTab(self)
        self.settings_tab = SettingsTab()
        self.tabs.addTab(self.main_tab, "Main")
        self.tabs.addTab(self.results_tab, "Results")
        self.tabs.addTab(self.queue_tab, "Queue")
        self.tabs.addTab(self.thresholds_tab, "Thresholds")
        self.tabs.addTab(self.settings_tab, "Settings")

        self.layout = QVBoxLayout()
        self.layout.addWidget(self.tabs)
        self.layout.setContentsMargins(10, 10, 10, 0)
        self.setLayout(self.layout)


class MainTab(SingleLinkableSetting, QFrame):
    set_progressbar_signal = pyqtSignal(int) # max progress
    increment_progressbar_signal = pyqtSignal(int) # increment value
    update_label_signal = pyqtSignal(str)
    write_to_terminal_signal = pyqtSignal(str)
    add_result_signal = pyqtSignal(object) # Result
    add_run_to_queue_signal = pyqtSignal(object) # Run object (or a subclass)
    update_run_status_signal = pyqtSignal(int, str) # run_id, status_str
    print_results_signal = pyqtSignal() # called after a run finishes to flush the results queue before printing "Done"

    LOADABLES_COMBOBOX_REGISTRY = ["Map Replay", "Local Replay", "Map", "User", "All Map Replays by User"]
    CHECKS_COMBOBOX_REGISTRY = ["Replay Stealing/Remodding", "Relax", "Aim Correction", "Visualize"]

    def __init__(self):
        QFrame.__init__(self)
        SingleLinkableSetting.__init__(self, "api_key")

        self.library = Library(get_setting("cache_dir"))

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
        self.visualizer = None

        terminal = QTextEdit(self)
        terminal.setFocusPolicy(Qt.ClickFocus)
        terminal.setReadOnly(True)
        terminal.ensureCursorVisible()
        self.terminal = terminal

        self.run_button = QPushButton()
        self.run_button.setText("Run")
        self.run_button.clicked.connect(self.add_circleguard_run)
        # disable button if no api_key is stored
        self.on_setting_changed("api_key", get_setting("api_key"))

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

    def on_setting_changed(self, setting, text):
        self.run_button.setEnabled(text != "")

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
        if button_data == "Visualize":
            w = VisualizerW()
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
                    if isinstance(loadableW, ReplayPathW):
                        loadable = ReplayPath(loadableW.path_input.path)
                    if isinstance(loadableW, ReplayMapW):
                        # Mod init errors on empty string, so just assign None
                        mods = Mod(loadableW.mods_input.value()) if loadableW.mods_input.value() else None
                        loadable = ReplayMap(int(loadableW.map_id_input.value()), int(loadableW.user_id_input.value()), mods=mods)
                    if isinstance(loadableW, MapW):
                        mods = Mod(loadableW.mods_input.value()) if loadableW.mods_input.value() else None
                        # use placeholder text (1-50) if the user inputted span is empty
                        span = loadableW.span_input.value() or loadableW.span_input.field.placeholderText()
                        if span == "all":
                            span = "1-100"
                        loadable = Map(int(loadableW.map_id_input.value()), span=span, mods=mods)
                    if isinstance(loadableW, UserW):
                        mods = Mod(loadableW.mods_input.value()) if loadableW.mods_input.value() else None
                        span=loadableW.span_input.value()
                        if span == "all":
                            span = "1-100"
                        loadable = User(int(loadableW.user_id_input.value()), span=span, mods=mods)
                    if isinstance(loadableW, MapUserW):
                        span = loadableW.span_input.value() or loadableW.span_input.field.placeholderText()
                        if span == "all":
                            span = "1-100"
                        loadable = MapUser(int(loadableW.map_id_input.value()), int(loadableW.user_id_input.value()), span=span)
                    loadableW_id_to_loadable[loadableW.loadable_id] = loadable
                except ValueError as e:
                    self.write_to_terminal_signal.emit(str(e))
                    self.update_label_signal.emit("Invalid arguments")
                    self.update_run_status_signal.emit(run.run_id, "Invalid arguments")
                    self.set_progressbar_signal.emit(-1)
                    sys.exit(0)

            for checkW in run.checks:
                d = None
                check_type = None
                max_angle = None
                min_distance = None
                if isinstance(checkW, StealCheckW):
                    check_type = "Steal"
                    d = Detect.STEAL
                if isinstance(checkW, RelaxCheckW):
                    check_type = "Relax"
                    d = Detect.RELAX
                if isinstance(checkW, CorrectionCheckW):
                    max_angle = get_setting("correction_max_angle")
                    min_distance = get_setting("correction_min_distance")
                    check_type = "Aim Correction"
                    d = Detect.CORRECTION
                if isinstance(checkW, VisualizerW):
                    d = Detect(0)  # don't run any detection
                    check_type = "Visualization"
                # retrieve loadable objects from loadableW ids
                if isinstance(checkW, StealCheckW):
                    loadables1 = [loadableW_id_to_loadable[loadableW.loadable_id] for loadableW in checkW.loadables1]
                    loadables2 = [loadableW_id_to_loadable[loadableW.loadable_id] for loadableW in checkW.loadables2]
                    c = Check(loadables1, cache=None, loadables2=loadables2)
                else:
                    loadables = [loadableW_id_to_loadable[loadableW.loadable_id] for loadableW in checkW.loadables]
                    c = Check(loadables, cache=None)
                message_loading_info = get_setting("message_loading_info").format(ts=datetime.now(), check_type=check_type)
                self.write_to_terminal_signal.emit(message_loading_info)
                cg.load_info(c)
                replays = c.all_replays()
                # don't show "loading 2 replays" if they were already loaded
                # by a previous check, would be misleading
                num_unloaded = 0
                num_total = len(c.all_replays())
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
                setting = "message_starting_investigation_visualization" if isinstance(checkW, VisualizerW) else "message_starting_investigation"
                message_starting_investigation = get_setting(setting).format(ts=datetime.now(),
                                num_total=num_total, num_previously_loaded=num_loaded, num_unloaded=num_unloaded,
                                check_type=check_type)
                self.write_to_terminal_signal.emit(message_starting_investigation)
                if isinstance(checkW, VisualizerW):
                    map_ids = [r.map_id for r in replays]
                    if len(set(map_ids)) != 1:
                        self.write_to_terminal_signal.emit(f"Visualizer expected replays from a single map, but got multiple {set(map_ids)}. Please use a different Visualizer Object for each map")
                        self.update_label_signal.emit("Visualizer Error (Multiple maps)")
                        self.update_run_status_signal.emit(run.run_id, "Visualizer Error (Multiple maps)")
                        self.set_progressbar_signal.emit(-1)
                        sys.exit(0)
                    self.q.put(replays)
                else:
                    self.update_label_signal.emit("Investigating Replays")
                    self.update_run_status_signal.emit(run.run_id, "Investigating Replays")
                    for result in cg.run(c.loadables1, d, c.loadables2, max_angle, min_distance):
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
                ischeat = False
                if isinstance(result, StealResult):
                    if result.similarity < get_setting("steal_max_sim"):
                        ischeat = True
                        message = get_setting("message_steal_found").format(ts=ts, sim=result.similarity, r=result, replay1=result.replay1, replay2=result.replay2,
                                                replay1_mods_short_name=result.replay1.mods.short_name(), replay1_mods_long_name=result.replay1.mods.long_name(),
                                                replay2_mods_short_name=result.replay2.mods.short_name(), replay2_mods_long_name=result.replay2.mods.long_name())
                    elif result.similarity < get_setting("steal_max_sim_display"):
                        message = get_setting("message_steal_found_display").format(ts=ts, sim=result.similarity, r=result, replay1=result.replay1,
                                                replay2=result.replay2, replay1_mods_short_name=result.replay1.mods.short_name(), replay1_mods_long_name=result.replay1.mods.long_name(),
                                                replay2_mods_short_name=result.replay2.mods.short_name(), replay2_mods_long_name=result.replay2.mods.long_name())

                if isinstance(result, RelaxResult):
                    if result.ur < get_setting("relax_max_ur"):
                        ischeat = True
                        message = get_setting("message_relax_found").format(ts=ts, r=result, replay=result.replay, ur=result.ur,
                                                mods_short_name=result.replay.mods.short_name(), mods_long_name=result.replay.mods.long_name())
                    elif result.ur < get_setting("relax_max_ur_display"):
                        message = get_setting("message_relax_found_display").format(ts=ts, r=result, replay=result.replay, ur=result.ur,
                                                mods_short_name=result.replay.mods.short_name(), mods_long_name=result.replay.mods.long_name())

                if isinstance(result, CorrectionResult):
                    if len(result.snaps) > 0:
                        ischeat = True
                        snap_message = get_setting("message_correction_snaps")
                        snap_text = "\n".join([snap_message.format(time=snap.time, angle=snap.angle, distance=snap.distance) for snap in result.snaps])
                        message = get_setting("message_correction_found").format(ts=ts, r=result, replay=result.replay, snaps=snap_text,
                                                mods_short_name=result.replay.mods.short_name(), mods_long_name=result.replay.mods.long_name())
                # message is None if the result isn't a cheat and doesn't
                # satisfy its display threshold
                if message:
                    self.write(message)
                if not isinstance(result, list): # not a list of loadables
                    if ischeat:
                        QApplication.beep()
                        QApplication.alert(self)
                        # add to Results Tab so it can be played back on demand
                        self.add_result_signal.emit(result)
                else:
                    self.add_result_signal.emit(result)

        except Empty:
            pass

    def visualize(self, replays, beatmap_id, result):
        # only run one instance at a time
        if self.visualizer is not None:
            self.visualizer.close()
        snaps = []
        if isinstance(result, CorrectionResult):
            snaps = [snap.time for snap in result.snaps]
        beatmap_info = BeatmapInfo(map_id=beatmap_id)
        if not get_setting("render_beatmap"):
            # don't give the visualizer any beatmap info if the user doesn't
            # want it rendered
            beatmap_info = BeatmapInfo()
        self.visualizer = CGVisualizer(beatmap_info, replays, snaps, self.library)
        self.visualizer.show()


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
        cache_path = get_setting("cache_dir") + "circleguard.db"
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

        self.open_settings = QPushButton("Open Advanced Settings")
        self.open_settings.clicked.connect(self._open_settings)
        self.sync_settings = QPushButton("Sync Settings")
        self.sync_settings.clicked.connect(self._sync_settings)


        self.info = QLabel(self)
        # multiple spaces get shrinked to one space in rich text mode
        # https://groups.google.com/forum/#!topic/qtcontribs/VDOQFUj-eIA
        self.info.setText(f"circleguard v{__version__}&nbsp;&nbsp;|&nbsp;&nbsp;"
                          f"circlecore v{cg_version}&nbsp;&nbsp;|&nbsp;&nbsp;"
                          f"<a href=\"https://github.com/circleguard/circleguard/issues\">Bug Report</a>")
        self.info.setTextFormat(Qt.RichText)
        self.info.setTextInteractionFlags(Qt.TextBrowserInteraction)
        self.info.setOpenExternalLinks(True)
        self.info.setAlignment(Qt.AlignCenter)
        self.setting_buttons = WidgetCombiner(self, self.open_settings, self.sync_settings)

        layout = QGridLayout()
        layout.addWidget(self.info, 0,0,1,1, alignment=Qt.AlignLeft)
        layout.addWidget(self.setting_buttons, 0,1,1,1, alignment=Qt.AlignRight)
        layout.addWidget(self.qscrollarea, 1,0,1,2)

        self.setLayout(layout)

    def _open_settings(self):
        overwrite_config() # generate file with latest changes
        QDesktopServices.openUrl(QUrl.fromLocalFile(get_setting("config_location") + "/circleguard.cfg"))

    def _sync_settings(self):
        overwrite_with_config_settings()


class ScrollableSettingsWidget(QFrame):
    """
    This class contains all of the actual settings content - SettingsTab just
    has a QScrollArea wrapped around this widget so that it can be scrolled
    down.

    """
    def __init__(self):
        super().__init__()
        self.visualizer = None
        self.wizard = CircleguardWizard()

        self.apikey_widget = LineEditSetting("Api Key", "", "password", "api_key")
        self.darkmode = OptionWidget("Dark mode", "Come join the dark side", "dark_theme")
        self.visualizer_info = OptionWidget("Show Visualizer info", "", "visualizer_info")
        self.visualizer_beatmap = OptionWidget("Render Hitobjects", "Reopen Visualizer for it to apply", "render_beatmap")
        self.cache = OptionWidget("Caching", "Downloaded replays will be cached locally", "caching")

        self.loglevel = LoglevelWidget("")

        self.run_wizard = ButtonWidget("Run Wizard", "Run", "")
        self.run_wizard.button.clicked.connect(self.show_wizard)

        vert_spacer = QSpacerItem(0, 10, QSizePolicy.Maximum, QSizePolicy.Minimum)
        self.layout = QVBoxLayout()
        self.layout.setAlignment(Qt.AlignTop)
        self.layout.addItem(vert_spacer)
        self.layout.addWidget(Separator("General"))
        self.layout.addWidget(self.apikey_widget)
        self.layout.addWidget(self.cache)
        self.layout.addItem(vert_spacer)
        self.layout.addWidget(Separator("Appearance"))
        self.layout.addWidget(self.darkmode)
        self.layout.addWidget(self.visualizer_info)
        self.layout.addWidget(self.visualizer_beatmap)
        self.layout.addItem(vert_spacer)
        self.layout.addWidget(Separator("Debug"))
        self.layout.addWidget(self.loglevel)
        self.layout.addWidget(ResetSettings())
        self.layout.addItem(vert_spacer)
        self.layout.addWidget(Separator("Dev"))
        self.layout.addWidget(self.run_wizard)
        self.beatmaptest = BeatmapTest()
        self.beatmaptest.button.clicked.connect(self.visualize)
        self.layout.addWidget(self.beatmaptest)
        self.setLayout(self.layout)

    def show_wizard(self):
        self.wizard.show()

    def visualize(self):
        if self.visualizer is not None:
            self.visualizer.close()
        beatmap_info = BeatmapInfo(path=self.beatmaptest.file_chooser.path)
        # TODO pass the library we define in MainTab to CGVIsualizer,
        # probably will have to rework some things entirely
        paint_info = get_setting("visualizer_info")
        self.visualizer = CGVisualizer(beatmap_info, paint_info=paint_info)
        self.visualizer.show()


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
    def __init__(self, parent):
        super().__init__(parent)
        self.qscrollarea = QScrollArea(self)
        self.qscrollarea.setWidget(ScrollableThresholdsWidget(self))
        self.qscrollarea.setWidgetResizable(True)

        self.layout = QVBoxLayout()
        self.layout.addWidget(self.qscrollarea)
        self.setLayout(self.layout)

class ScrollableThresholdsWidget(QFrame):
    def __init__(self, parent):
        super().__init__(parent)
        self.steal_max_sim = SliderBoxSetting(self, "Max similarity", "ReplaySteal comparisons that score below this "
                "will be stored so you can view them, and printed to the console", "steal_max_sim", 100)
        self.steal_max_sim_display = SliderBoxSetting(self, "Max similarity display", "ReplaySteal comparisons that "
                "score below this will be printed to the console", "steal_max_sim_display", 100)
        self.relax_max_ur = SliderBoxSetting(self, "Max ur", "Replays that have a ur lower than this will be stored "
                "so you can view them, and printed to the console", "relax_max_ur", 300)
        self.relax_max_ur_display = SliderBoxSetting(self, "Max ur display", "Replays with a ur lower than this "
                "will be printed to the console", "relax_max_ur_display", 300)
        # display options for correction are more confusing than they're worth,
        # especially when we don't have a good mechanism for storing Snaps in
        # the Result tab or visualizer support for the Snap timestamps. TODO
        # potentially add back if we can provide good support for them.
        self.correction_max_angle = SliderBoxSetting(self, "Max angle", "Replays with a set of three points "
                "making an angle less than this (*and* also satisfying correction_min_distance) will be stored so "
                "you can view them, and printed to the console.", "correction_max_angle", 360)
        self.correction_min_distance = SliderBoxSetting(self, "Min distance", "Replays with a set of three points "
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
