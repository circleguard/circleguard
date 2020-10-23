from queue import Queue, Empty
import threading
from datetime import datetime
import sys
import math
import time
from functools import partial
import itertools
import logging
import re
from lzma import LZMAError
import traceback

from PyQt5.QtCore import pyqtSignal, QObject, Qt
from PyQt5.QtWidgets import (QMessageBox, QFrame, QGridLayout, QComboBox,
    QTextEdit, QScrollArea, QPushButton, QApplication, QToolTip)
from PyQt5.QtGui import QTextCursor
# from circleguard import (Circleguard, ReplayDir, ReplayPath, Mod,
    # UnknownAPIException, NoInfoAvailableException, ReplayMap, Map, User,
    # MapUser, Detect, Check, TimewarpResult, RelaxResult, CorrectionResult,
    # StealResult, Loader, replay_pairs)
# from slider import Library
# from circlevis import BeatmapInfo

from widgets import (ReplayMapW, ReplayPathW, MapW, UserW, MapUserW,
    ScrollableLoadablesWidget, ScrollableChecksWidget, StealCheckW, RelaxCheckW,
    CorrectionCheckW, TimewarpCheckW, AnalyzeW)
from settings import SingleLinkableSetting, get_setting, set_setting
from utils import (delete_widget, AnalysisResult, StealResult, RelaxResult,
    CorrectionResult, TimewarpResult)
from .visualizer import get_visualizer


log = logging.getLogger("circleguard_gui")

class MainTab(SingleLinkableSetting, QFrame):
    set_progressbar_signal = pyqtSignal(int) # max progress
    increment_progressbar_signal = pyqtSignal(int) # increment value
    update_label_signal = pyqtSignal(str)
    write_to_terminal_signal = pyqtSignal(str)
    add_result_signal = pyqtSignal(object) # Result
    add_url_analysis_result_signal = pyqtSignal(object) # URLAnalysisResult
    add_run_to_queue_signal = pyqtSignal(object) # Run object (or a subclass)
    update_run_status_signal = pyqtSignal(int, str) # run_id, status_str
    print_results_signal = pyqtSignal() # called after a run finishes to flush the results queue before printing "Done"

    LOADABLES_COMBOBOX_REGISTRY = ["Add a Loadable", "+ Map Replay", "+ Local Replay", "+ Map", "+ User", "+ All User Replays on Map"]
    CHECKS_COMBOBOX_REGISTRY = ["Add an Investigation", "+ Similarity", "+ Unstable Rate", "+ Snaps", "+ Frametime", "+ Manual Analysis"]

    def __init__(self):
        QFrame.__init__(self)
        SingleLinkableSetting.__init__(self, "api_key")

        # lazy loaded, see self#library
        self._library = None

        self.loadables_combobox = QComboBox(self)
        self.loadables_combobox.setInsertPolicy(QComboBox.NoInsert)
        for loadable in MainTab.LOADABLES_COMBOBOX_REGISTRY:
            self.loadables_combobox.addItem(loadable, loadable)
        self.loadables_combobox.activated.connect(self.add_loadable)

        self.checks_combobox = QComboBox(self)
        self.checks_combobox.setInsertPolicy(QComboBox.NoInsert)
        for check in MainTab.CHECKS_COMBOBOX_REGISTRY:
            self.checks_combobox.addItem(check, check)
        self.checks_combobox.activated.connect(self.add_check)

        self.loadables_scrollarea = QScrollArea(self)
        self.loadables_scrollarea.setWidget(ScrollableLoadablesWidget())
        self.loadables_scrollarea.setWidgetResizable(True)

        self.checks_scrollarea = QScrollArea(self)
        self.checks_scrollarea.setWidget(ScrollableChecksWidget())
        self.checks_scrollarea.setWidgetResizable(True)

        self.loadables = [] # for deleting later
        self.checks = [] # for deleting later

        self.print_results_signal.connect(self.print_results)
        self.write_to_terminal_signal.connect(self.write)

        self.q = Queue()
        # `AnalysisResult`s get put here when we get a url scheme event, we need
        # to create the visualizer from the main thread so we use a queue to
        # kick back the work to the main thread. This is checked at the same
        # time `self.q` is
        self.url_analysis_q = Queue()
        # reset at the beginning of every run, used to print something after
        # every run only if a cheat wasn't found
        self.show_no_cheat_found = True
        self.print_results_event = threading.Event()
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

        self.run_button = RunButton()
        self.run_button.setFixedHeight(30)
        self.run_button.setText("Run")
        font = self.run_button.font()
        font.setPointSize(15)
        self.run_button.setFont(font)
        self.run_button.clicked.connect(self.add_circleguard_run)
        # disable button if no api_key is stored
        self.on_setting_changed("api_key", get_setting("api_key"))

        layout = QGridLayout()
        layout.addWidget(self.loadables_combobox, 0, 0, 1, 4)
        layout.addWidget(self.checks_combobox, 0, 8, 1, 4)
        layout.addWidget(self.loadables_scrollarea, 1, 0, 4, 8)
        layout.addWidget(self.checks_scrollarea, 1, 8, 4, 8)
        layout.addWidget(self.terminal, 5, 0, 2, 16)
        layout.addWidget(self.run_button, 7, 0, 1, 16)

        self.setLayout(layout)

    def on_setting_changed(self, setting, text):
        # TODO `setting_value` should be updated automatically by
        # `LinkableSetting`
        self.setting_value = text
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
        # don't do anything if they selected the default text
        if self.loadables_combobox.currentIndex() == 0:
            return
        button_data = self.loadables_combobox.currentData()
        # go back to default text
        self.loadables_combobox.setCurrentIndex(0)
        if button_data == "+ Map Replay":
            w = ReplayMapW()
        if button_data == "+ Local Replay":
            w = ReplayPathW()
        if button_data == "+ Map":
            w = MapW()
        if button_data == "+ User":
            w = UserW()
        if button_data == "+ All User Replays on Map":
            w = MapUserW()
        w.remove_loadable_signal.connect(self.remove_loadable)
        self.loadables_scrollarea.widget().layout.addWidget(w)
        self.loadables.append(w)
        self.check_drag_loadables_tutorial()

    def add_check(self):
        if self.checks_combobox.currentIndex() == 0:
            return
        button_data = self.checks_combobox.currentData()
        self.checks_combobox.setCurrentIndex(0)
        if button_data == "+ Similarity":
            w = StealCheckW()
        if button_data == "+ Unstable Rate":
            w = RelaxCheckW()
        if button_data == "+ Snaps":
            w = CorrectionCheckW()
        if button_data == "+ Frametime":
            w = TimewarpCheckW()
        if button_data == "+ Manual Analysis":
            w = AnalyzeW()
        w.remove_check_signal.connect(self.remove_check)
        self.checks_scrollarea.widget().layout.addWidget(w)
        self.checks.append(w)
        self.check_drag_loadables_tutorial()

    def check_drag_loadables_tutorial(self):
        # don't play the message if they don't have both a loadable and a check
        if len(self.loadables) < 1 or len(self.checks) < 1:
            return
        # don't play the message more than once
        if get_setting("tutorial_drag_loadables_seen"):
            return

        message_box = QMessageBox()
        message_box.setText("In order to investigate a Loadable, drag it from "
            "the left <------- and drop it onto a Check on the right ------>, then hit run.")
        message_box.exec()

        set_setting("tutorial_drag_loadables_seen", True)

    def write(self, message):
        self.terminal.append(str(message).strip())
        self.scroll_to_bottom()

    def scroll_to_bottom(self):
        cursor = QTextCursor(self.terminal.document())
        cursor.movePosition(QTextCursor.End)
        self.terminal.setTextCursor(cursor)

    @property
    def library(self):
        if not self._library:
            from slider import Library
            self._library = Library(get_setting("cache_dir"))
        return self._library

    def add_circleguard_run(self):
        # osu!api v2 uses a client secret which is still 40 chars long but
        # includes characters after f, unlike v1's key which is in hex.
        if re.search("[g-z]", self.setting_value):
            message_box = QMessageBox()
            message_box.setTextFormat(Qt.RichText)
            message_box.setText("Your api key is invalid. You are likely using "
                    "an api v2 key.\n"
                    "Please ensure your api key comes from "
                    "<a href=\"https://osu.ppy.sh/p/api\">https://osu.ppy.sh/p/api</a>.")
            message_box.exec()
            return
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
        from circleguard import (Circleguard, ReplayDir, ReplayPath, Mod,
            UnknownAPIException, NoInfoAvailableException, ReplayMap, Map, User,
            MapUser, Loader, LoadableContainer, replay_pairs)
        class TrackerLoader(Loader, QObject):
            """
            A circleguard.Loader subclass that emits a signal when the loader is
            ratelimited. It inherits from QObject to allow us to use qt signals.
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

        self.update_label_signal.emit("Loading Replays")
        self.update_run_status_signal.emit(run.run_id, "Loading Replays")
        # reset every run
        self.show_no_cheat_found = True
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
                        if loadableW.path_input.path.is_dir():
                            loadable = ReplayDir(loadableW.path_input.path)
                        else:
                            loadable = ReplayPath(loadableW.path_input.path)
                    if isinstance(loadableW, ReplayMapW):
                        # Mod init errors on empty string, so just assign None
                        mods = Mod(loadableW.mods_input.value()) if loadableW.mods_input.value() else None
                        loadable = ReplayMap(int(loadableW.map_id_input.value()), int(loadableW.user_id_input.value()), mods=mods)
                    if isinstance(loadableW, MapW):
                        mods = Mod(loadableW.mods_input.value()) if loadableW.mods_input.value() else None
                        # use placeholder text (eg 1-50) if the user inputted span is empty
                        span = loadableW.span_input.value() or loadableW.span_input.field.placeholderText()
                        if span == "all":
                            span = Loader.MAX_MAP_SPAN
                        loadable = Map(int(loadableW.map_id_input.value()), span=span, mods=mods)
                    if isinstance(loadableW, UserW):
                        mods = Mod(loadableW.mods_input.value()) if loadableW.mods_input.value() else None
                        span = loadableW.span_input.value() or loadableW.span_input.field.placeholderText()
                        if span == "all":
                            span = Loader.MAX_USER_SPAN
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
                check_type = None
                max_angle = None
                min_distance = None

                if isinstance(checkW, StealCheckW):
                    check_type = "Steal"
                if isinstance(checkW, RelaxCheckW):
                    check_type = "Relax"
                if isinstance(checkW, CorrectionCheckW):
                    max_angle = get_setting("correction_max_angle")
                    min_distance = get_setting("correction_min_distance")
                    check_type = "Aim Correction"
                if isinstance(checkW, TimewarpCheckW):
                    check_type = "Timewarp"
                if isinstance(checkW, AnalyzeW):
                    check_type = "Visualization"

                # retrieve loadable objects from loadableW ids
                if isinstance(checkW, StealCheckW):
                    loadables1 = [loadableW_id_to_loadable[loadableW.loadable_id] for loadableW in checkW.loadables1]
                    loadables2 = [loadableW_id_to_loadable[loadableW.loadable_id] for loadableW in checkW.loadables2]
                    lc1 = LoadableContainer(loadables1)
                    lc2 = LoadableContainer(loadables2)
                else:
                    loadables = [loadableW_id_to_loadable[loadableW.loadable_id] for loadableW in checkW.loadables]
                    lc = LoadableContainer(loadables)
                message_loading_info = get_setting("message_loading_info").format(ts=datetime.now(), check_type=check_type)
                self.write_to_terminal_signal.emit(message_loading_info)

                if isinstance(checkW, StealCheckW):
                    cg.load_info(lc1)
                    cg.load_info(lc2)
                    replays1 = lc1.all_replays()
                    replays2 = lc2.all_replays()
                    all_replays = replays1 + replays2
                else:
                    cg.load_info(lc)
                    all_replays = lc.all_replays()
                    replays1 = all_replays
                    replays2 = []

                # don't show "loading 2 replays" if they were already loaded
                # by a previous check, would be misleading
                num_unloaded = 0
                num_total = len(all_replays)
                for r in all_replays:
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


                def _skip_replay_with_message(replay, message):
                    self.write_to_terminal_signal.emit(message)
                    # the replay very likely (perhaps certainly) didn't get
                    # loaded if the above exception fired. just skip it.
                    all_replays.remove(replay)
                    # check has already been initialized with the replay,
                    # remove it here too or cg will try and load it again
                    # when the check is ran
                    if replay in replays1:
                        replays1.remove(replay)
                    if replay in replays2:
                        replays2.remove(replay)

                # `[:]` implicitly copies the list, so we don't run into trouble
                #  when removing elements from it while iterating
                for replay in all_replays[:]:
                    _check_event(event)
                    try:
                        cg.load(replay)
                        if not replay.has_data():
                            _skip_replay_with_message(replay, "<div style='color:crimson'>The replay " + str(replay) + " is " +
                                "not available for download.</div>This is likely because it is not in the top 1k scores of "
                                "the beatmap. This replay has been skipped because of this.")
                    except NoInfoAvailableException as e:
                        _skip_replay_with_message(replay, "<div style='color:crimson'>The replay " + str(replay) + " does "
                            "not exist.</div>\nDouble check your map and/or user id. This replay has "
                            "been skipped because of this.")
                    except UnknownAPIException as e:
                        _skip_replay_with_message(replay, "<div style='color:crimson'>The osu! api provided an invalid "
                            "response:</div> " + str(e) + ". The replay " + str(replay) + " has been skipped because of this.")
                    except LZMAError as e:
                        _skip_replay_with_message(replay, "<div style='color:crimson'>lzma error while parsing a replay:</div> " + str(e) +
                            ". The replay is either corrupted or has no replay data. The replay " + str(replay) +
                            " has been skipped because of this.")
                    except Exception as e:
                        # print full traceback here for more debugging info.
                        # Don't do it for the previous exceptions because the
                        # cause of those is well understood, but that's not
                        # necessarily the case for generic exceptions here.

                        # attempting to use divs/spans here to color the beginning
                        # of this string made the traceback collapse down into
                        # one line with none of the usual linebreaks, I'm not
                        # sure why. So you win qt, no red color for this error.
                        _skip_replay_with_message(replay, "error while loading a replay: " + str(e) + "\n" +
                                traceback.format_exc() +
                                "The replay " + str(replay) + " has been skipped because of this.")
                    finally:
                        self.increment_progressbar_signal.emit(1)

                if isinstance(checkW, StealCheckW):
                    lc1.loaded = True
                    lc2.loaded = True
                else:
                    lc.loaded = True
                # change progressbar into an undetermined state (animation with
                # stripes sliding horizontally) to indicate we're processing
                # the data
                self.set_progressbar_signal.emit(0)
                setting_end_dict = {
                    StealCheckW: "steal",
                    RelaxCheckW: "relax",
                    CorrectionCheckW: "correction",
                    TimewarpCheckW: "timewarp",
                    AnalyzeW: "analysis"
                }
                setting = f"message_starting_" + setting_end_dict[type(checkW)]
                message_starting_investigation = get_setting(setting).format(ts=datetime.now())
                self.write_to_terminal_signal.emit(message_starting_investigation)
                if isinstance(checkW, AnalyzeW):
                    map_ids = [r.map_id for r in all_replays]
                    if len(set(map_ids)) > 1:
                        self.write_to_terminal_signal.emit("Manual analysis expected replays from a single map, "
                            f"but got replays from maps {set(map_ids)}. Please use a different Manual Analysis "
                            "Check for each map.")
                        self.update_label_signal.emit("Analysis Error (Multiple maps)")
                        self.update_run_status_signal.emit(run.run_id, "Analysis Error (Multiple maps)")
                        self.set_progressbar_signal.emit(-1)
                        sys.exit(0)
                    # if a replay was removed from all_replays (eg if that replay was not available for download),
                    # and that leaves all_replays with no replays, we don't want to add a result because
                    # the rest of guard expects >=1 replay, leading to confusing errors.
                    if len(all_replays) != 0:
                        self.q.put(AnalysisResult(all_replays))
                else:
                    self.update_label_signal.emit("Investigating Replays...")
                    self.update_run_status_signal.emit(run.run_id, "Investigating Replays")

                    if isinstance(checkW, StealCheckW):
                        pairs = replay_pairs(replays1, replays2)
                        for (replay1, replay2) in pairs:
                            _check_event(event)
                            sim = cg.similarity(replay1, replay2)
                            result = StealResult(sim, replay1, replay2)
                            self.q.put(result)
                    if isinstance(checkW, RelaxCheckW):
                        for replay in all_replays:
                            _check_event(event)
                            # skip replays which have no map info
                            if replay.map_info.available():
                                ur = cg.ur(replay)
                                result = RelaxResult(ur, replay)
                                self.q.put(result)
                            else:
                                self.write_to_terminal_signal.emit("<div style='color:crimson'>The "
                                    "replay " + str(replay) + " has no map id</div>, so its ur cannot "
                                    "be calculated. This replay has been skipped because of this.")
                    if isinstance(checkW, CorrectionCheckW):
                        for replay in all_replays:
                            _check_event(event)
                            snaps = cg.snaps(replay, max_angle, min_distance)
                            result = CorrectionResult(snaps, replay)
                            self.q.put(result)
                    if isinstance(checkW, TimewarpCheckW):
                        for replay in all_replays:
                            _check_event(event)
                            frametime = cg.frametime(replay)
                            frametimes = cg.frametimes(replay)
                            result = TimewarpResult(frametime, frametimes, replay)
                            self.q.put(result)

                self.print_results_signal.emit() # flush self.q

            self.set_progressbar_signal.emit(-1) # empty progressbar
            # this event is necessary because `print_results` will set
            # `show_no_cheat_found`, and since it happens asynchronously we need
            # to wait for it to finish before checking it. So we clear it here,
            # then wait for it to get set before proceeding.
            self.print_results_event.clear()
            # 'flush' self.q so there's no more results left and message_finished_investigation
            # won't print before results from that investigation which looks strange.
            # Signal instead of call to be threadsafe and avoid
            # ```
            # QObject::connect: Cannot queue arguments of type 'QTextCursor'
            # (Make sure 'QTextCursor' is registered using qRegisterMetaType().)
            # ```
            # warning
            self.print_results_signal.emit()
            self.print_results_event.wait()
            if self.show_no_cheat_found:
                self.write_to_terminal_signal.emit(get_setting("message_no_cheat_found").format(ts=datetime.now()))
            self.write_to_terminal_signal.emit(get_setting("message_finished_investigation").format(ts=datetime.now()))
            # prevents an error when a user closes the application. Because
            # we're running inside a new thread, if we don't do this, cg (and)
            # the library) will get gc'd in another thread. Because library's
            # ``__del__`` closes the sqlite connection, this causes:
            # ```
            # Traceback (most recent call last):
            # File "/Users/tybug/Desktop/coding/osu/slider/slider/library.py", line 98, in __del__
            #   self.close()
            # File "/Users/tybug/Desktop/coding/osu/slider/slider/library.py", line 94, in close
            #   self._db.close()
            # sqlite3.ProgrammingError: SQLite objects created in a thread can only be used in that same thread.
            # The object was created in thread id 123145483210752 and this is thread id 4479481280.
            # ```
            cg.library.close()

        except Exception:
            # if the error happens before we set the progressbar it stays at
            # 100%. make sure we reset it here
            self.set_progressbar_signal.emit(-1)
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
                                        earlier_replay_mods_short_name=result.earlier_replay.mods.short_name(), earlier_replay_mods_long_name=result.earlier_replay.mods.long_name(),
                                        later_replay_mods_short_name=result.later_replay.mods.short_name(), later_replay_mods_long_name=result.later_replay.mods.long_name())
                    elif result.similarity < get_setting("steal_max_sim_display"):
                        message = get_setting("message_steal_found_display").format(ts=ts, sim=result.similarity, r=result, replay1=result.replay1,
                                        earlier_replay_mods_short_name=result.earlier_replay.mods.short_name(), earlier_replay_mods_long_name=result.earlier_replay.mods.long_name(),
                                        later_replay_mods_short_name=result.later_replay.mods.short_name(), later_replay_mods_long_name=result.later_replay.mods.long_name())

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

                if isinstance(result, TimewarpResult):
                    if result.frametime < get_setting("timewarp_max_frametime"):
                        ischeat = True
                        message = get_setting("message_timewarp_found").format(ts=ts, r=result, replay=result.replay, frametime=result.frametime,
                                                mods_short_name=result.replay.mods.short_name(), mods_long_name=result.replay.mods.long_name())
                    elif result.frametime < get_setting("timewarp_max_frametime_display"):
                        message = get_setting("message_timewarp_found_display").format(ts=ts, r=result, replay=result.replay, frametime=result.frametime,
                                                mods_short_name=result.replay.mods.short_name(), mods_long_name=result.replay.mods.long_name())

                if message or isinstance(result, AnalysisResult):
                    self.show_no_cheat_found = False
                if message:
                    self.write(message)
                if isinstance(result, AnalysisResult):
                    self.add_result_signal.emit(result)
                else:
                    if ischeat:
                        QApplication.beep()
                        QApplication.alert(self)
                        # add to Results Tab so it can be played back on demand
                        self.add_result_signal.emit(result)

        except Empty:
            try:
                result = self.url_analysis_q.get_nowait()
                self.add_url_analysis_result_signal.emit(result)
            except Empty:
                pass
        self.print_results_event.set()

    def visualize(self, replays, beatmap_id, result, start_at=0):
        from circlevis import BeatmapInfo
        # only run one instance at a time
        if self.visualizer is not None:
            self.visualizer.close()
        snaps = []
        if isinstance(result, CorrectionResult):
            snaps = [snap.time for snap in result.snaps]
        beatmap_info = BeatmapInfo(map_id=beatmap_id)
        CGVisualizer = get_visualizer()
        self.visualizer = CGVisualizer(beatmap_info, replays, snaps, self.library)
        self.visualizer.show()
        if start_at != 0:
            self.visualizer.seek_to(start_at)
            self.visualizer.pause()

    def visualize_from_url(self, result):
        """
        called when our url scheme (circleguard://) was entered, giving
        us a replay to visualize
        """
        map_id = result.replays[0].map_id
        if self.visualizer and self.visualizer.isVisible() and self.visualizer.replays and self.visualizer.replays[0].map_id == map_id:
            # pause even if we're currently playing - it's important that this
            # happens before seeking, or else the new frame won't correctly
            # display
            self.visualizer.force_pause()
            # if we're visualizing the same replay that's in the url, just jump
            # to the new timestamp
            self.visualizer.seek_to(result.timestamp)
            return
        # otherwise visualize as normal (which will close any existing
        # visualizers)
        self.visualize(result.replays, map_id, result, start_at=result.timestamp)


class Run():
    """
    Represents a click of the Run button on the Main tab, which can contain
    multiple Checks, each of which contains a set of Loadables.
    """
    def __init__(self, checks, run_id, event):
        self.checks = checks
        self.run_id = run_id
        self.event = event

class RunButton(QPushButton):

    def __init__(self):
        super().__init__()

    def enterEvent(self, event):
        if not self.isEnabled():
            QToolTip.showText(event.globalPos(), "You cannot run an investigation until you enter an api key in settings.")
