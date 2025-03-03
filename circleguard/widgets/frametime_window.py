from PyQt6.QtWidgets import QMainWindow
from PyQt6.QtGui import QIcon
from utils import resource_path

from widgets.fratetime_graph import FrametimeGraph


class FrametimeWindow(QMainWindow):
    def __init__(self, replay):
        super().__init__()
        # XXX make sure to import matplotlib after pyqt, so it knows to use that
        # and not re-import it.
        from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT

        self.setWindowTitle("Replay Frametime")
        self.setWindowIcon(QIcon(resource_path("logo/logo.ico")))

        frametime_graph = FrametimeGraph(replay)
        self.addToolBar(NavigationToolbar2QT(frametime_graph.canvas, self))
        self.setCentralWidget(frametime_graph)
        self.resize(600, 500)
