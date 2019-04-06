import sys
import os
from pathlib import Path
from multiprocessing.pool import ThreadPool
from queue import Queue, Empty
from functools import partial

# pylint: disable=no-name-in-module
from PyQt5.QtCore import Qt, QRegExp, QTimer, QSettings
from PyQt5.QtWidgets import (QWidget, QTabWidget, QTextEdit, QPushButton, QLabel,
                             QSpinBox, QVBoxLayout, QSlider, QDoubleSpinBox, QLineEdit,
                             QCheckBox, QGridLayout, QApplication, QSpacerItem, QSizePolicy)
from PyQt5.QtGui import QPalette, QColor, QRegExpValidator, QIcon, QKeyEvent
# pylint: enable=no-name-in-module

from circleguard import *
from circleguard import __version__ as cg_version
from widgets import *


ROOT_PATH = Path(__file__).parent
__version__ = "0.1d"
print(f"backend {cg_version}, frontend {__version__}")


def resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)


def reset_defaults():
    settings.setValue("ran", True)
    settings.setValue("threshold", 18)
    settings.setValue("api_key", "")
    settings.setValue("dark_theme", 0)
    settings.setValue("caching", 0)


settings = QSettings("Circleguard", "Circleguard")
RAN_BEFORE = settings.value("ran")

if not RAN_BEFORE:
    reset_defaults()

THRESHOLD = settings.value("threshold")
API_KEY = settings.value("api_key")
DARK_THEME = settings.value("dark_theme")
CACHING = settings.value("caching")


class MainWindow(QWidget):
    def __init__(self):
        super(MainWindow, self).__init__()

        self.tabWidget = QTabWidget()
        self.tabWidget.addTab(MainTab(), "Main Tab")
        self.tabWidget.addTab(SettingsWindow(), "Settings Tab")

        self.mainLayout = QVBoxLayout()
        self.mainLayout.addWidget(self.tabWidget)
        self.setLayout(self.mainLayout)

        self.setWindowTitle(f"Circleguard (Backend v{cg_version} / Frontend v{__version__})")

        # use this if we have an icon for the program
        self.setWindowIcon(QIcon(str(resource_path("resources/logo.ico"))))


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
        self.installEventFilter(self)

    # necessary to catch arrow key events for some reason
    def eventFilter(self, source, event):
        if event.type() == QKeyEvent:
            self.keyPressEvent(event)
        return super(MainTab, self).eventFilter(source, event)

    def keyPressEvent(self, event):
        # switch between Map/User/Local/Verify tabs
        if event.key() == Qt.Key_Right:
            self.tabs.setCurrentIndex(self.tabs.currentIndex() + 1)
        if event.key() == Qt.Key_Left:
            self.tabs.setCurrentIndex(self.tabs.currentIndex() - 1)

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
        self.info.setText("Compare the top n plays of a Map's leaderboard")

        self.map_id = MapId()
        self.compare_top = CompareTop()
        self.threshold = Threshold()

        layout = QGridLayout()
        layout.addWidget(self.info, 0, 0, 1, -1)
        layout.addWidget(self.map_id, 1, 0, 1, -1)
        layout.addWidget(self.compare_top, 2, 0, 1, -1)
        layout.addWidget(self.threshold, 3, 0, 1, -1)

        self.setLayout(layout)


class UserTab(QWidget):
    def __init__(self):
        super(UserTab, self).__init__()
        self.info = QLabel(self)
        self.info.setText("This will compare a user's n top plays with the n Top plays of the corresponding Map")
        self.grid = QGridLayout()
        self.grid.addWidget(self.info, 0, 0, 1, 1)
        self.setLayout(self.grid)


class UserOnMapTab(QWidget):
    def __init__(self):
        super(UserOnMapTab, self).__init__()
        self.info = QLabel(self)
        self.info.setText("This will compare a user's score with the n Top plays of a Map")
        self.grid = QGridLayout()
        self.grid.addWidget(self.info, 0, 0, 1, 1)
        self.setLayout(self.grid)


class LocalTab(QWidget):
    def __init__(self):
        super(LocalTab, self).__init__()
        self.info = QLabel(self)
        self.info.setText("This will verify replays")
        self.grid = QGridLayout()
        self.grid.addWidget(self.info, 0, 0, 1, 1)
        self.setLayout(self.grid)


class VerifyTab(QWidget):
    def __init__(self):
        super(VerifyTab, self).__init__()
        self.info = QLabel(self)
        self.info.setText("This will compare a user's score with the n Top plays of a Map")
        self.grid = QGridLayout()
        self.grid.addWidget(self.info, 0, 0, 1, 1)
        self.setLayout(self.grid)


class SettingsWindow(QWidget):
    def __init__(self):
        super(SettingsWindow, self).__init__()
        self.darkmode_label = QLabel(self)
        self.darkmode_label.setText("Dark mode:")
        self.darkmode_label.setToolTip("tmp")

        self.darkmode_box = QCheckBox(self)
        self.darkmode_box.setToolTip("tmp")
        self.darkmode_box.stateChanged.connect(switch_theme)
        self.darkmode_box.setChecked(DARK_THEME)

        self.thresh_label = QLabel(self)
        self.thresh_label.setText("Default Threshold:")
        self.thresh_label.setToolTip("tmp")

        self.thresh_value = QSpinBox()
        self.thresh_value.setValue(THRESHOLD)
        self.thresh_value.setAlignment(Qt.AlignCenter)
        self.thresh_value.setRange(0, 30)
        self.thresh_value.setSingleStep(1)
        self.thresh_value.valueChanged.connect(partial(update_default, "threshold"))
        self.thresh_value.setToolTip("tmp")

        self.apikey_label = QLabel(self)
        self.apikey_label.setText("API Key:")

        self.apikey_field = QLineEdit(self)
        self.apikey_field.setText(API_KEY)
        self.apikey_field.textChanged.connect(partial(update_default, "api_key"))
        self.apikey_field.textChanged.connect(set_api_key)

        self.cache_label = QLabel(self)
        self.cache_label.setText("Caching:")
        self.cache_label.setToolTip("Downloaded replays will be cached locally")

        self.cache_box = QCheckBox(self)
        self.cache_box.stateChanged.connect(partial(update_default, "caching"))
        self.cache_box.setChecked(CACHING)

        self.grid = QGridLayout()
        self.grid.addWidget(self.apikey_label, 0, 0, 1, 1)
        self.grid.addWidget(self.apikey_field, 0, 1, 1, 1)
        self.grid.addWidget(self.thresh_label, 1, 0, 1, 1)
        self.grid.addWidget(self.thresh_value, 1, 1, 1, 1)
        self.grid.addWidget(self.darkmode_label, 2, 0, 1, 1)
        self.grid.addWidget(self.darkmode_box, 2, 1, 1, 1)
        self.grid.addWidget(self.cache_label, 3, 0, 1, 1)
        self.grid.addWidget(self.cache_box, 3, 1, 1, 1)
        self.setLayout(self.grid)


def update_default(name, value):
    settings.setValue(name, value)

def set_api_key():
    global API_KEY
    API_KEY = settings.value("api_key")

def switch_theme(dark):
    update_default("dark_theme", 1 if dark else 0)
    if dark:
        dark_palette = QPalette()

        dark_palette.setColor(QPalette.Window, QColor(53, 53, 53))
        dark_palette.setColor(QPalette.WindowText, Qt.white)
        dark_palette.setColor(QPalette.Base, QColor(25, 25, 25))
        dark_palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
        dark_palette.setColor(QPalette.ToolTipBase, QColor(53, 53, 53))
        dark_palette.setColor(QPalette.ToolTipText, Qt.white)
        dark_palette.setColor(QPalette.Text, Qt.white)
        dark_palette.setColor(QPalette.Button, QColor(53, 53, 53))
        dark_palette.setColor(QPalette.ButtonText, Qt.white)
        dark_palette.setColor(QPalette.BrightText, Qt.red)
        dark_palette.setColor(QPalette.Link, QColor(42, 130, 218))
        dark_palette.setColor(QPalette.Highlight, QColor(218, 130, 42))
        dark_palette.setColor(QPalette.Inactive, QPalette.Highlight, Qt.lightGray)
        dark_palette.setColor(QPalette.HighlightedText, Qt.black)
        dark_palette.setColor(QPalette.Disabled, QPalette.Text, Qt.darkGray)
        dark_palette.setColor(QPalette.Disabled, QPalette.ButtonText, Qt.darkGray)
        dark_palette.setColor(QPalette.Disabled, QPalette.Highlight, Qt.darkGray)

        app.setPalette(dark_palette)
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
    window = MainWindow()
    window.resize(600, 500)
    window.show()
    app.exec_()
