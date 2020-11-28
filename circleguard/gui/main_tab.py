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
    QTextEdit, QScrollArea, QApplication, QToolTip, QLabel,
    QSizePolicy)
from PyQt5.QtGui import QTextCursor
import requests
# from circleguard import (Circleguard, ReplayDir, ReplayPath, Mod,
    # UnknownAPIException, NoInfoAvailableException, ReplayMap, Map, User,
    # MapUser, Detect, Check, TimewarpResult, RelaxResult, CorrectionResult,
    # StealResult, Loader, replay_pairs)
# from slider import Library
# from circlevis import BeatmapInfo

from widgets import (ReplayMapW, ReplayPathW, MapW, UserW, MapUserW,
    ScrollableLoadablesWidget, ScrollableChecksWidget, StealCheckW, RelaxCheckW,
    CorrectionCheckW, TimewarpCheckW, AnalyzeW, InvestigationCheckboxes,
    WidgetCombiner, PushButton, LoadableCreation)
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

    def __init__(self):
        QFrame.__init__(self)
        SingleLinkableSetting.__init__(self, "api_key")

        # lazy loaded, see self#library
        self._library = None

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
        self.runs = [] # Run objects for cancelling runs
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

        investigate_label = QLabel("Investigate For:")
        investigate_label.setFixedWidth(130)
        investigate_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        self.investigation_checkboxes = InvestigationCheckboxes()
        investigations = WidgetCombiner(investigate_label, self.investigation_checkboxes, self)
        investigations.setFixedHeight(25)

        self.loadable_creation = LoadableCreation()

        self.investigation_checkboxes.similarity_cb.checkbox.stateChanged.connect(self.loadable_creation.similarity_cb_state_changed)

        layout = QGridLayout()
        layout.addWidget(investigations, 0, 0, 1, 16)
        layout.addWidget(self.loadable_creation, 1, 0, 4, 16)
        layout.addWidget(self.terminal, 5, 0, 2, 16)
        layout.addWidget(self.run_button, 7, 0, 1, 16)

        self.setLayout(layout)

    def on_setting_changed(self, setting, text):
        # TODO `setting_value` should be updated automatically by
        # `LinkableSetting`
        self.setting_value = text
        self.run_button.setEnabled(text != "")

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

        if not self.loadable_creation.check_and_mark_required_fields():
            return

        # loadables can have their required fields filled, but with invalid
        # input, like having "1a" as a span. In this case we print the error
        # and early return.
        try:
            loadables = self.loadable_creation.cg_loadables()
        except ValueError as e:
            self.write_to_terminal_signal.emit(f"<div style='color:#ff5252'>Invalid arguments:</div> {str(e)}")
            return

        enabled_investigations = self.investigation_checkboxes.enabled_investigations()
        # if no loadables have been filled out, don't proceed
        if not loadables:
            return
        # similarly for investigations, but give a heads up since this mistake
        # is slightly subtler
        if not enabled_investigations:
            # nbsp is necessary because apparently ending with a closing tag
            # makes qt not recognize it and causes all text afterwards to be
            # affected by the div's color
            self.write_to_terminal_signal.emit("<div style='color:#ff5252'>You must select "
                "at least one investigation before running</div>&nbsp")
            return

        run = Run(loadables, enabled_investigations, self.run_id, threading.Event())
        self.runs.append(run)
        self.add_run_to_queue_signal.emit(run)
        self.cg_q.put(run)
        self.run_id += 1

        # called every 1/4 seconds by timer, but force a recheck so we don't
        # wait for that delay
        self.check_circleguard_queue()


    def check_circleguard_queue(self):
        def _check_circleguard_queue(self):
            try:
                while True:
                    run = self.cg_q.get_nowait()
                    # occurs if run is canceled before being started, it will
                    # still stop before actually loading anything but we don't
                    # want the labels to flicker
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
                # we do this loop in order to tell run_circleguard to check if
                # the run was canceled, or the application quit, instead of
                # hanging on a long time.sleep
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

            if "Similarity" in run.enabled_investigations:
                loadables1 = []
                loadables2 = []
                for loadable in run.loadables:
                    if loadable.sim_group == 1:
                        loadables1.append(loadable)
                    else:
                        loadables2.append(loadable)
                lc1 = LoadableContainer(loadables1)
                lc2 = LoadableContainer(loadables2)
            else:
                lc = LoadableContainer(run.loadables)
            message_loading_info = get_setting("message_loading_info").format(ts=datetime.now())
            self.write_to_terminal_signal.emit(message_loading_info)

            if "Similarity" in run.enabled_investigations:
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

            num_replays = len(all_replays)
            self.set_progressbar_signal.emit(num_replays)
            message_loading_replays = get_setting("message_loading_replays").format(ts=datetime.now(),
                            num_replays=num_replays)
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
                        _skip_replay_with_message(replay, "<div style='color:#ff5252'>The replay " + str(replay) + " is " +
                            "not available for download.</div>This is likely because it is not in the top 1k scores of "
                            "the beatmap. This replay has been skipped because of this.")
                except NoInfoAvailableException as e:
                    _skip_replay_with_message(replay, "<div style='color:#ff5252'>The replay " + str(replay) + " does "
                        "not exist.</div>\nDouble check your map and/or user id. This replay has "
                        "been skipped because of this.")
                except UnknownAPIException as e:
                    _skip_replay_with_message(replay, "<div style='color:#ff5252'>The osu! api provided an invalid "
                        "response:</div> " + str(e) + ". The replay " + str(replay) + " has been skipped because of this.")
                except LZMAError as e:
                    _skip_replay_with_message(replay, "<div style='color:#ff5252'>lzma error while parsing a replay:</div> " + str(e) +
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

            if "Similarity" in run.enabled_investigations:
                lc1.loaded = True
                lc2.loaded = True
            else:
                lc.loaded = True
            # change progressbar into an undetermined state (animation with
            # stripes sliding horizontally) to indicate we're processing
            # the data
            self.set_progressbar_signal.emit(0)
            setting_end_dict = {
                "Similarity": "steal",
                "Unstable Rate": "relax",
                "Snaps": "correction",
                "Frametime": "timewarp",
                "Manual Analysis": "analysis"
            }
            for investigation in run.enabled_investigations:
                setting = f"message_starting_" + setting_end_dict[investigation]
                message_starting_investigation = get_setting(setting).format(ts=datetime.now())
                self.write_to_terminal_signal.emit(message_starting_investigation)
                if investigation == "Manual Analysis":
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
                    continue
                self.update_label_signal.emit("Investigating Replays...")
                self.update_run_status_signal.emit(run.run_id, "Investigating Replays")

                if investigation == "Similarity":
                    pairs = replay_pairs(replays1, replays2)
                    for (replay1, replay2) in pairs:
                        _check_event(event)
                        sim = cg.similarity(replay1, replay2)
                        result = StealResult(sim, replay1, replay2)
                        self.q.put(result)
                if investigation == "Unstable Rate":
                    for replay in all_replays:
                        _check_event(event)
                        # skip replays which have no map info
                        if replay.map_info.available():
                            try:
                                ur = cg.ur(replay)
                            # Sometimes, a beatmap will have a bugged download where it returns an empty response
                            # when we try to download it (https://github.com/ppy/osu-api/issues/171). Since peppy
                            # doesn't plan on fixing this for unranked beatmaps, we just ignore / skip the error
                            # in all cases.
                            # StopIteration is a bit of a weird exception to catch here, but because of how slider
                            # interacts with beatmaps it will attempt to call `next` on an empty generator if the
                            # beatmap is empty, which of course raises StopIteration.
                            except StopIteration:
                                if requests.get(f"https://osu.ppy.sh/osu/{replay.map_id}").content == b"":
                                    self.write_to_terminal_signal.emit("<div style='color:#ff5252'>The "
                                        "map " + str(replay.map_id) + "'s download is bugged</div>, so its ur cannot "
                                        "be calculated. The replay " + str(replay) + " has been skipped because of this, "
                                        "but please report this to the developers through discord or github so it can be "
                                        "tracked.")
                                    break
                                # If we happen to catch an unrelated error with this `except`, we still want to
                                # raise that so it can be tracked and fixed.
                                else:
                                    raise
                            result = RelaxResult(ur, replay)
                            self.q.put(result)
                        else:
                            self.write_to_terminal_signal.emit("<div style='color:#ff5252'>The "
                                "replay " + str(replay) + " has no map id</div>, so its ur cannot "
                                "be calculated. This replay has been skipped because of this.")
                if investigation == "Snaps":
                    max_angle = get_setting("correction_max_angle")
                    min_distance = get_setting("correction_min_distance")

                    for replay in all_replays:
                        _check_event(event)
                        snaps = cg.snaps(replay, max_angle, min_distance)
                        result = CorrectionResult(snaps, replay)
                        self.q.put(result)
                if investigation == "Frametime":
                    for replay in all_replays:
                        _check_event(event)
                        frametime = cg.frametime(replay)
                        frametimes = cg.frametimes(replay)
                        result = TimewarpResult(frametime, frametimes, replay)
                        self.q.put(result)

                # flush self.q. Since the next investigation will be processed
                # so quickly afterwards, we actually need to forcibly wait
                # until the results have been printed before proceeding.
                self.print_results_event.clear()
                self.print_results_signal.emit()
                self.print_results_event.wait()

            self.set_progressbar_signal.emit(-1) # empty progressbar
            # this event is necessary because `print_results` will set
            # `show_no_cheat_found`, and since it happens asynchronously we need
            # to wait for it to finish before checking it. So we clear it here,
            # then wait for it to get set before proceeding.
            self.print_results_event.clear()
            # 'flush' self.q so there's no more results left and message_finished_investigation
            # won't print before results from that investigation which looks strange.
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
    Represents a click of the Run button on the Main tab, which contains a set
    of loadables and a list of investigations enabled for those loadables.
    """
    def __init__(self, loadables, enabled_investigations, run_id, event):
        self.loadables = loadables
        self.enabled_investigations = enabled_investigations
        self.run_id = run_id
        self.event = event

class RunButton(PushButton):
    def __init__(self):
        super().__init__()

    def enterEvent(self, event):
        if not self.isEnabled():
            QToolTip.showText(event.globalPos(), "You cannot run an investigation until you enter an api key in settings.")
