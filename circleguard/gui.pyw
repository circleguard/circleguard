import sys
import os
from pathlib import Path
from multiprocessing.pool import ThreadPool
from queue import Queue, Empty
from functools import partial

# pylint: disable=no-name-in-module
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import (QWidget, QTabWidget, QTextEdit, QPushButton, QLabel,
                             QVBoxLayout, QShortcut, QGridLayout, QApplication, QMainWindow)
from PyQt5.QtGui import QPalette, QColor, QIcon, QKeySequence
# pylint: enable=no-name-in-module

from circleguard import Circleguard
from circleguard import __version__ as cg_version

from widgets import (Threshold, set_event_window, IdWidget, CompareTop,
                     FolderChoose, SpinBox, InputWidget, OptionWidget, ThresholdCombined)
from settings import THRESHOLD, API_KEY, DARK_THEME, CACHING, update_default, CACHE_DIR

ROOT_PATH = Path(__file__).parent
__version__ = "0.1d"
print(f"backend {cg_version}, frontend {__version__}")


def resource_path(*args):
    """
    Returns a Path representing where to look for resource files for the program,
    such as databases or images.

    This location changes if the program is run from an application built with pyinstaller.
    """
    if hasattr(sys, '_MEIPASS'):  # being run from a pyinstall'd app
        return os.path.join(sys._MEIPASS, *args)  # pylint: disable=no-member
    return os.path.join(os.path.abspath("."), *args)


class WindowWrapper(QMainWindow):
    def __init__(self):
        super(WindowWrapper, self).__init__()
        self.main_window = MainWindow()
        self.setCentralWidget(self.main_window)
        self.show()
        QShortcut(QKeySequence(Qt.CTRL+Qt.Key_Right), self, self.tab_right)
        QShortcut(QKeySequence(Qt.CTRL+Qt.Key_Left), self, self.tab_left)

        self.setWindowTitle(f"Circleguard (Backend v{cg_version} / Frontend v{__version__})")

        self.setWindowIcon(QIcon(str(resource_path("resources", "logo.ico"))))

    # I know, I know...we have a stupid amount of layers.
    # WindowWrapper -> MainWindow -> MainTab -> Tabs
    def tab_right(self):
        tabs = self.main_window.main_tab.tabs
        tabs.setCurrentIndex(tabs.currentIndex() + 1)

    def tab_left(self):
        tabs = self.main_window.main_tab.tabs
        tabs.setCurrentIndex(tabs.currentIndex() - 1)


class MainWindow(QWidget):
    def __init__(self):
        super(MainWindow, self).__init__()

        self.tab_widget = QTabWidget()
        self.main_tab = MainTab()
        self.settings_tab = SettingsTab()
        self.tab_widget.addTab(self.main_tab, "Main Tab")
        self.tab_widget.addTab(self.settings_tab, "Settings Tab")

        self.main_layout = QVBoxLayout()
        self.main_layout.addWidget(self.tab_widget)
        self.setLayout(self.main_layout)

    def mousePressEvent(self, event):
        focused = self.focusWidget()
        if focused is not None:
            focused.clearFocus()
        super(MainWindow, self).mousePressEvent(event)


class MainTab(QWidget):
    def __init__(self):
        super(MainTab, self).__init__()
        self.q = Queue()

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

        terminal = QTextEdit()
        terminal.setReadOnly(True)
        self.terminal = terminal

        self.run_button = QPushButton()
        self.run_button.setText("Run")
        self.run_button.clicked.connect(self.run)

        layout = QVBoxLayout()
        layout.addWidget(tabs)
        layout.addWidget(self.terminal)
        layout.addWidget(self.run_button)
        self.setLayout(layout)

        self.start_timer()

    def start_timer(self):
        timer = QTimer(self)
        timer.timeout.connect(self.print_results)
        timer.start(250)

    def write(self, text):
        self.terminal.append(str(text).strip())

    def reset_scrollbar(self):
        self.terminal.verticalScrollBar().setValue(self.terminal.verticalScrollBar().maximum())

    def run(self):
        pool = ThreadPool(processes=1)
        pool.apply_async(self.run_circleguard)

    def run_circleguard(self):
        print("running")
        cg = Circleguard(API_KEY, str(resource_path("db/cache.db")))
        map_id = int(self.map_tab.map_id.field.text())
        num = self.map_tab.compare_top.slider.value()
        thresh = self.map_tab.threshold.slider.value()
        cg_map = cg.map_check(map_id, num=num, thresh=thresh)
        for result in cg_map:
            self.q.put(result)

    def print_results(self):
        try:
            while True:
                result = self.q.get(block=False)
                if result.ischeat:
                    self.write(f"{result.similiarity:0.1f} similarity. {result.replay1.username} vs {result.replay2.username}, {result.later_name} set later")
        except Empty:
            pass


class MapTab(QWidget):
    def __init__(self):
        super(MapTab, self).__init__()

        self.info = QLabel(self)
        self.info.setText("Compare the top n plays of a Map's leaderboard.\nIf a user is given, it will compare the "
                          "user against the maps leaderboard.")

        self.map_id = IdWidget("Map Id", "Beatmap id, not the mapset id!")
        self.user_id = IdWidget("User Id", "User id, as seen in the profile url")
        self.compare_top = CompareTop()
        self.threshold = ThresholdCombined()

        layout = QGridLayout()
        layout.addWidget(self.info, 0, 0, 1, 1)
        layout.addWidget(self.map_id, 1, 0, 1, 1)
        layout.addWidget(self.user_id, 2, 0, 1, 1)
        layout.addWidget(self.compare_top, 3, 0, 1, 1)
        layout.addWidget(self.threshold, 4, 0, 1, 1)

        self.setLayout(layout)


class UserTab(QWidget):
    def __init__(self):
        super(UserTab, self).__init__()
        self.info = QLabel(self)
        self.info.setText("This will compare a user's n top plays with the n Top plays of the corresponding Map")

        self.user_id = IdWidget("User Id", "User id, as seen in the profile url")
        self.compare_top = CompareTop()
        self.threshold = Threshold()

        layout = QGridLayout()
        layout.addWidget(self.info, 0, 0, 1, 1)
        layout.addWidget(self.user_id, 1, 0, 1, 1)
        layout.addWidget(self.compare_top, 2, 0, 1, 1)
        layout.addWidget(self.threshold, 3, 0, 1, 1)

        self.setLayout(layout)


class LocalTab(QWidget):
    def __init__(self):
        super(LocalTab, self).__init__()
        self.info = QLabel(self)
        self.info.setText("This will verify replays")
        self.file_chooser = FolderChoose("Replay folder")
        self.grid = QGridLayout()
        self.grid.addWidget(self.info, 0, 0, 1, 1)
        self.grid.addWidget(self.file_chooser, 1, 0, 1, 1)
        self.setLayout(self.grid)


class VerifyTab(QWidget):
    def __init__(self):
        super(VerifyTab, self).__init__()
        self.info = QLabel(self)
        self.info.setText("This will compare a user's score with the n Top plays of a Map")
        self.grid = QGridLayout()
        self.grid.addWidget(self.info, 0, 0, 1, 1)
        self.setLayout(self.grid)


class SettingsTab(QWidget):
    def __init__(self):
        super(SettingsTab, self).__init__()
        self.info = QLabel(self)
        self.info.setText(f"Backend Version : {cg_version}<br/>"
                          f"Frontend Version : {__version__}<br/>"
                          f"Repository : <a href=\"https://github.com/circleguard/circleguard\">github.com/circleguard/circleguard</a>")
        self.info.setTextFormat(Qt.RichText)
        self.info.setTextInteractionFlags(Qt.TextBrowserInteraction)
        self.info.setOpenExternalLinks(True)
        self.info.setAlignment(Qt.AlignCenter)

        self.apikey_widget = InputWidget("Api Key", "")
        self.apikey_widget.field.textChanged.connect(partial(update_default, "api_key"))
        self.apikey_widget.field.textChanged.connect(set_api_key)

        self.thresh_widget = Threshold()
        self.thresh_widget.thresh_spinbox.valueChanged.connect(partial(update_default, "threshold"))

        self.darkmode = OptionWidget("Dark mode", "")
        self.darkmode.box.stateChanged.connect(switch_theme)
        self.darkmode.box.setChecked(DARK_THEME)

        self.cache = OptionWidget("Caching", "Downloaded replays will be cached locally")
        self.cache.box.stateChanged.connect(partial(update_default, "caching"))
        self.cache.box.setChecked(CACHING)

        self.cache_dir = FolderChoose("Cache Path")
        self.cache_dir.path_signal.connect(partial(update_default, "cache_dir"))
        self.cache_dir.update_dir(CACHE_DIR)

        self.grid = QGridLayout()
        self.grid.addWidget(self.info, 0, 0, 1, 1)
        self.grid.addWidget(self.apikey_widget, 1, 0, 1, 1)
        self.grid.addWidget(self.thresh_widget, 2, 0, 1, 1)
        self.grid.addWidget(self.cache_dir, 3, 0, 1, 1)
        self.grid.addWidget(self.cache, 4, 0, 1, 1)
        self.grid.addWidget(self.darkmode, 5, 0, 1, 1)
        self.setLayout(self.grid)


def set_api_key(key):
    global API_KEY
    API_KEY = key


def switch_theme(dark):
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
        dark_p.setColor(QPalette.Link, QColor(42, 130, 218))
        dark_p.setColor(QPalette.Highlight, QColor(218, 130, 42))
        dark_p.setColor(QPalette.Inactive, QPalette.Highlight, Qt.lightGray)
        dark_p.setColor(QPalette.HighlightedText, Qt.black)
        dark_p.setColor(QPalette.Disabled, QPalette.Text, Qt.darkGray)
        dark_p.setColor(QPalette.Disabled, QPalette.ButtonText, Qt.darkGray)
        dark_p.setColor(QPalette.Disabled, QPalette.Highlight, Qt.darkGray)

        app.setPalette(dark_p)
        app.setStyleSheet("QToolTip { color: #ffffff; "
                          "background-color: #2a2a2a; "
                          "border: 1px solid white; }")
    else:
        app.setPalette(app.style().standardPalette())
        updated_palette = QPalette()
        # fixes inactive items not being greyed out
        updated_palette.setColor(QPalette.Disabled, QPalette.ButtonText, Qt.darkGray)
        updated_palette.setColor(QPalette.Disabled, QPalette.Highlight, Qt.darkGray)
        updated_palette.setColor(QPalette.Inactive, QPalette.Highlight, QColor(240, 240, 240))
        app.setPalette(updated_palette)
        app.setStyleSheet("QToolTip { color: #000000; "
                          "background-color: #D5D5D5; "
                          "border: 1px solid white; }")


if __name__ == "__main__":
    # create and open window
    app = QApplication([])
    app.setStyle("Fusion")
    WINDOW = WindowWrapper()
    set_event_window(WINDOW)
    WINDOW.resize(600, 500)
    WINDOW.show()
    app.exec_()
