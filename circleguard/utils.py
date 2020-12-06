from pathlib import Path
import sys

from PyQt5.QtWidgets import QLayout, QFrame, QSpacerItem, QSizePolicy
from PyQt5.QtGui import QPainter, QColor

# the blue accent color used throughout the application
ACCENT_COLOR = QColor(71, 174, 247)

# placed above local imports to avoid circular import errors
ROOT_PATH = Path(__file__).parent.parent.absolute()
def resource_path(path):
    """
    Get the resource path for a given file.

    This location changes if the program is run from an application built with
    pyinstaller.

    Returns
    -------
    string
        The absolute path (as a string) to the given file, after taking into
        account whether we are running in a development setting.
        Return string because this function is almost always used in a ``QIcon``
        context, which does not accept a ``Path``.
    """

    if hasattr(sys, '_MEIPASS'): # being run from a pyinstall'd app
        return str(Path(sys._MEIPASS) / "resources" / Path(path)) # pylint: disable=no-member
    return str(ROOT_PATH / "resources" / Path(path))


# TODO figure out if ``delete_widget`` (and ``clear_layout``) are really
# necessary instead of just using ``widget.deleteLater``
def delete_widget(widget):
    if widget.layout is not None:
        clear_layout(widget.layout)
        widget.layout = None
    widget.deleteLater()


def clear_layout(layout):
    while layout.count():
        child = layout.takeAt(0)
        if child.layout() is not None:
            clear_layout(child.layout())
        if child.widget() is not None:
            if isinstance(child.widget().layout, QLayout):
                clear_layout(child.widget().layout)
            child.widget().deleteLater()


class DebugWidget(QFrame):
    """
    A class intended to be subclassed by widgets when debugging. This draws
    rectangles around all items of the class's layout.
    """

    # methods adapted from https://doc.qt.io/qt-5/qlayout.html#itemAt
    def paintEvent(self, paintEvent):
        painter = QPainter(self)
        self.paintLayout(painter, self.layout)

    def paintLayout(self, painter, item):
        layout = item.layout()
        if layout:
            for i in range(layout.count()):
                self.paintLayout(painter, layout.itemAt(i))
        painter.drawRect(item.geometry())

class StealResult():
    def __init__(self, similarity, replay1, replay2):
        from circleguard import order
        self.similarity = similarity
        self.replay1 = replay1
        self.replay2 = replay2
        (self.earlier_replay, self.later_replay) = order(replay1, replay2)

class RelaxResult():
    def __init__(self, ur, replay):
        self.ur = ur
        self.replay = replay

class CorrectionResult():
    def __init__(self, snaps, replay):
        self.snaps = snaps
        self.replay = replay

class TimewarpResult():
    def __init__(self, frametime, frametimes, replay):
        self.frametime = frametime
        self.frametimes = frametimes
        self.replay = replay

class AnalysisResult():
    def __init__(self, replays):
        self.replays = replays

class URLAnalysisResult():
    def __init__(self, replays, timestamp):
        self.replays = replays
        self.timestamp = timestamp

# reusing qt widgets is a BIG mistake (leads to, for example, segfaults when
# deleting an item because it's trying to remove something that's being used
# elsewhere). We use identical spacer items across the gui but don't want to
# reuse the actual object, so this generates a new one for us.
def spacer():
    return QSpacerItem(100, 0, QSizePolicy.Maximum, QSizePolicy.Minimum)
