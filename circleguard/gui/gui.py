import os
from queue import Queue, Empty
from functools import partial
import logging
import threading

from PyQt5.QtCore import Qt, pyqtSignal, QUrl, QTimer
from PyQt5.QtWidgets import (QTabWidget, QVBoxLayout, QFrame, QScrollArea,
    QLabel, QPushButton, QGridLayout, QSpacerItem, QSizePolicy, QMainWindow,
    QTextEdit, QStackedWidget, QHBoxLayout, QMessageBox)
from PyQt5.QtGui import QDesktopServices, QIcon

# from circleguard import Circleguard, ReplayPath
# from circleguard import __version__ as cg_version
# from circlevis import BeatmapInfo

from utils import resource_path
from widgets import (ResetSettings, WidgetCombiner, FolderChooser, Separator,
    ButtonWidget, OptionWidget, SliderBoxMaxInfSetting, SliderBoxSetting,
    LineEditSetting, EntryWidget, RunWidget, ComboboxSetting, ReplayDropArea,
    ReplayMapCreation)

from settings import get_setting, set_setting, overwrite_config, overwrite_with_config_settings
from .visualizer import get_visualizer
from .main_tab import MainTab
from wizard import TutorialWizard
from version import __version__


log = logging.getLogger("circleguard_gui")


class MainWidget(QFrame):
    def __init__(self):
        super().__init__()
        self.back_button = QPushButton()
        self.back_button.setFixedWidth(55)
        self.back_button.setFixedHeight(30)
        self.back_button.setIcon(QIcon(resource_path("back_arrow.png")))
        # so we can reference just this button in css
        self.back_button.setObjectName("backButton")
        self.back_button.clicked.connect(lambda: self.set_index(0))
        # offset by a bit so we're not right against the window border
        margins = self.back_button.contentsMargins()
        margins.setLeft(10)
        margins.setTop(10)
        self.back_button.setContentsMargins(margins)

        self.stacked_widget = QStackedWidget()

        window_selector = WindowSelector()
        window_selector.visualize_button_clicked.connect(lambda: self.set_index(1))
        window_selector.bulk_investigation_button_clicked.connect(lambda: self.set_index(2))


        self.analysis_selection = AnalysisSelection()
        self.cg_classic = CircleguardClassic()

        self.stacked_widget.addWidget(window_selector)
        self.stacked_widget.addWidget(self.analysis_selection)
        self.stacked_widget.addWidget(self.cg_classic)

        index_map = {
            "selection": 0,
            "visualization": 1,
            "investigation": 2
        }
        index = index_map[get_setting("default_page")]
        self.set_index(index)

        layout = QVBoxLayout()
        layout.addWidget(self.back_button)
        layout.addWidget(self.stacked_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.setLayout(layout)

    def set_index(self, index):
        # don't show the back button on the selection page itself
        self.back_button.hide() if index == 0 else self.back_button.show()
        self.stacked_widget.setCurrentIndex(index)



class WindowSelector(QFrame):
    visualize_button_clicked = pyqtSignal()
    bulk_investigation_button_clicked = pyqtSignal()

    def __init__(self):
        super().__init__()

        visualize_button = QPushButton("Visualization")
        visualize_button.clicked.connect(self.visualize_button_clicked)
        # to style it in our stylesheet
        visualize_button.setObjectName("bigButton")

        bulk_investigation_button = QPushButton("Investigation / Settings")
        bulk_investigation_button.clicked.connect(self.bulk_investigation_button_clicked)
        bulk_investigation_button.setObjectName("bigButton")

        for button in [visualize_button, bulk_investigation_button]:
            font = button.font()
            font.setPointSize(30)
            button.setFont(font)

            expanding = QSizePolicy()
            expanding.setHorizontalPolicy(QSizePolicy.Expanding)
            expanding.setVerticalPolicy(QSizePolicy.Expanding)
            button.setSizePolicy(expanding)

        layout = QHBoxLayout()
        layout.addWidget(visualize_button)
        layout.addWidget(bulk_investigation_button)
        layout.setContentsMargins(15, 15, 15, 10)
        self.setLayout(layout)



class AnalysisSelection(QFrame):
    set_progressbar_signal = pyqtSignal(int)
    increment_progressbar_signal = pyqtSignal(int)
    update_label_signal = pyqtSignal(str)
    # used for cross-thread communication between loading the loadables (work
    # thread) and showing the visualizer (main thread)
    show_visualizer_window = pyqtSignal()

    def __init__(self):
        super().__init__()
        self._cg = None
        self.show_visualizer_window.connect(self.show_visualizer)

        expanding = QSizePolicy()
        expanding.setHorizontalPolicy(QSizePolicy.Expanding)
        expanding.setVerticalPolicy(QSizePolicy.Expanding)

        self.drop_area = ReplayDropArea()
        self.drop_area.setSizePolicy(expanding)
        da_scroll_area = QScrollArea(self)
        da_scroll_area.setWidget(self.drop_area)
        da_scroll_area.setWidgetResizable(True)
        da_scroll_area.setFrameShape(QFrame.NoFrame)

        self.replay_map_creation = ReplayMapCreation()
        self.replay_map_creation.setSizePolicy(expanding)
        rmc_scroll_area = QScrollArea(self)
        rmc_scroll_area.setWidget(self.replay_map_creation)
        rmc_scroll_area.setWidgetResizable(True)
        rmc_scroll_area.setFrameShape(QFrame.NoFrame)

        visualize_button = QPushButton("Visualize")
        visualize_button.setObjectName("bigButton")
        visualize_button.clicked.connect(self.visualize)
        font = visualize_button.font()
        font.setPointSize(30)
        visualize_button.setFont(font)
        expanding = QSizePolicy()
        expanding.setHorizontalPolicy(QSizePolicy.Expanding)
        expanding.setVerticalPolicy(QSizePolicy.Expanding)
        visualize_button.setSizePolicy(expanding)

        layout = QGridLayout()
        layout.addWidget(da_scroll_area, 0, 0, 6, 1)
        layout.addWidget(rmc_scroll_area, 0, 1, 6, 1)
        layout.addWidget(visualize_button, 6, 0, 2, 2)
        self.setLayout(layout)

    @property
    def cg(self):
        if not self._cg:
            from circleguard import Circleguard
            cache_path = get_setting("cache_dir") + "circleguard.db"
            self._cg = Circleguard(get_setting("api_key"), cache_path)
        return self._cg

    def all_loadables(self):
        return self.replay_map_creation.all_loadables() + self.drop_area.all_loadables()

    def visualize(self):
        # `#loadLoadables` will emit a signal to `show_visualizer_window` which
        # will call `show_visualizer`, so this call does eventually show the
        # visualizer, despite appearences otherwise
        thread = threading.Thread(target=self.load_loadables)
        thread.start()

    def show_visualizer(self):
        from circlevis import BeatmapInfo
        loadables = self.all_loadables()
        map_ids = [loadable.map_id for loadable in loadables]

        # if there are any duplicate maps, warn the user and don't proceed
        if len(set(map_ids)) > 1:
            message_box = QMessageBox()
            message_box.setText(f"You can only visualize replays from the same "
                f"map. The map ids present are {', '.join(str(map_id) for map_id in map_ids)}.")
            message_box.exec()
            return

        beatmap_info = BeatmapInfo(map_id=loadables[0].map_id)
        CGVisualizer = get_visualizer()

        # TODO reuse global library here
        self.visualizer = CGVisualizer(beatmap_info, loadables)
        self.visualizer.show()

    def load_loadables(self):
        loadables = self.all_loadables()
        # no loadables, user has clicked "visualize" without filling anything
        # out
        if not loadables:
            return

        self.update_label_signal.emit("Loading Replays")
        # len is fine here because they're all single loadables, not containers
        self.set_progressbar_signal.emit(len(loadables))
        for loadable in loadables:
            self.increment_progressbar_signal.emit(1)
            self.cg.load(loadable)


        self.set_progressbar_signal.emit(-1)
        self.update_label_signal.emit("Idle")
        self.show_visualizer_window.emit()


class CircleguardClassic(QFrame):
    def __init__(self):
        super().__init__()

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


# TODO needs to be updated to work with ReplayChooser instead of FolderChooser
class VisualizeTab(QFrame):
    def __init__(self):
        super().__init__()
        self.result_frame = ResultsTab()
        self.result_frame.results.info_label.hide()
        self.map_id = None
        self.q = Queue()
        self.replays = []
        # lazy loaded, see self.#cg
        self._cg = None
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

    @property
    def cg(self):
        if not self._cg:
            from circleguard import Circleguard
            cache_path = get_setting("cache_dir") + "circleguard.db"
            self._cg = Circleguard(get_setting("api_key"), cache_path)
        return self._cg

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
        from circleguard import ReplayPath
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
                          f"<a href=\"https://discord.gg/wj35ehD\">Discord</a>")
        self.info.setTextFormat(Qt.RichText)
        self.info.setTextInteractionFlags(Qt.TextBrowserInteraction)
        self.info.setOpenExternalLinks(True)
        self.info.setAlignment(Qt.AlignCenter)
        self.setting_buttons = WidgetCombiner(self.open_settings, self.sync_settings, self)

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

        self.apikey_widget = LineEditSetting("Api Key", "", "password", "api_key")
        self.theme = ComboboxSetting("Theme", "Come join the dark side", "theme")
        self.show_cv_frametimes = ComboboxSetting("Frametime graph display type", "", "frametime_graph_display")
        self.default_page = ComboboxSetting("Show this window when circleguard starts", "", "default_page")
        self.cache = OptionWidget("Caching", "Downloaded replays will be cached locally", "caching")
        self.default_span_map = LineEditSetting("Map span defaults to", "", "normal", "default_span_map")
        self.default_span_user = LineEditSetting("User span defaults to", "", "normal", "default_span_user")

        self.log_level = ComboboxSetting("Log Level", "", "log_level")
        self.log_output = ComboboxSetting("Log Output", "", "_log_output")

        self.run_wizard = ButtonWidget("Tutorial", "Read Tutorial", "")
        self.run_wizard.button.clicked.connect(self.show_wizard)

        vert_spacer = QSpacerItem(0, 10, QSizePolicy.Maximum, QSizePolicy.Minimum)
        self.layout = QVBoxLayout()
        self.layout.setAlignment(Qt.AlignTop)
        self.layout.addItem(vert_spacer)
        self.layout.addWidget(Separator("General"))
        self.layout.addWidget(self.apikey_widget)
        self.layout.addWidget(self.cache)
        self.layout.addWidget(self.theme)
        self.layout.addWidget(self.show_cv_frametimes)
        self.layout.addWidget(self.default_page)
        self.layout.addItem(vert_spacer)
        self.layout.addItem(vert_spacer)
        self.layout.addWidget(Separator("Loadables"))
        self.layout.addWidget(self.default_span_user)
        self.layout.addWidget(self.default_span_map)
        self.layout.addItem(vert_spacer)
        self.layout.addWidget(Separator("Debug"))
        self.layout.addWidget(self.log_level)
        self.layout.addWidget(self.log_output)
        self.layout.addWidget(ResetSettings())
        self.layout.addItem(vert_spacer)
        self.layout.addWidget(Separator("Dev"))
        self.layout.addWidget(self.run_wizard)
        self.setLayout(self.layout)

    def show_wizard(self):
        # keep a reference or it immediately deallocates
        self.wizard = TutorialWizard()
        self.wizard.show()


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
        steal_max_sim = SliderBoxMaxInfSetting(self, "Max similarity", "ReplaySteal comparisons that score below this "
                "will be stored so you can view them, and printed to the console", "steal_max_sim", 100)
        steal_max_sim_display = SliderBoxMaxInfSetting(self, "Max similarity display", "ReplaySteal comparisons that "
                "score below this will be printed to the console", "steal_max_sim_display", 100)
        relax_max_ur = SliderBoxMaxInfSetting(self, "Max ur", "Replays that have a ur lower than this will be stored "
                "so you can view them, and printed to the console", "relax_max_ur", 300)
        relax_max_ur_display = SliderBoxMaxInfSetting(self, "Max ur display", "Replays with a ur lower than this "
                "will be printed to the console", "relax_max_ur_display", 300)
        # display options for correction are more confusing than they're worth,
        # especially when we don't have a good mechanism for storing Snaps in
        # the Result tab or visualizer support for the Snap timestamps. TODO
        # potentially add back if we can provide good support for them.
        correction_max_angle = SliderBoxSetting(self, "Max angle", "Replays with a set of three points "
                "making an angle less than this (*and* also satisfying correction_min_distance) will be stored so "
                "you can view them, and printed to the console.", "correction_max_angle", 360)
        correction_min_distance = SliderBoxMaxInfSetting(self, "Min distance", "Replays with a set of three points "
                "where either the distance from AB or BC is greater than this (*and* also satisfying correction_max_angle) "
                "will be stored so you can view them, and printed to the console.", "correction_min_distance", 100)

        timewarp_max_frametime = SliderBoxMaxInfSetting(self, "Max frametime", "Replays with an average frametime "
                "lower than this will be stored so you can view them, and printed to the console", "timewarp_max_frametime", 50)
        timewarp_max_frametime_display = SliderBoxMaxInfSetting(self, "Max frametime display", "Replays with an average frametime "
                "lower than this will be printed to the console", "timewarp_max_frametime_display", 50)


        layout = QVBoxLayout()
        layout.addWidget(Separator("Replay Stealing"))
        layout.addWidget(steal_max_sim)
        layout.addWidget(steal_max_sim_display)
        layout.addWidget(Separator("Relax"))
        layout.addWidget(relax_max_ur)
        layout.addWidget(relax_max_ur_display)
        layout.addWidget(Separator("Aim Correction"))
        layout.addWidget(correction_max_angle)
        layout.addWidget(correction_min_distance)
        layout.addWidget(Separator("Timewarp"))
        layout.addWidget(timewarp_max_frametime)
        layout.addWidget(timewarp_max_frametime_display)

        layout.setAlignment(Qt.AlignTop)
        self.setLayout(layout)
