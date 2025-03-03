from PyQt6.QtWidgets import QMainWindow
from PyQt6.QtGui import QIcon
from utils import resource_path
from widgets.replay_data_table import ReplayDataTable

class ReplayDataWindow(QMainWindow):
    def __init__(self, replay):
        super().__init__()
        self.setWindowTitle("Raw Replay Data")
        self.setWindowIcon(QIcon(resource_path("logo/logo.ico")))

        replay_data_table = ReplayDataTable(replay)
        self.setCentralWidget(replay_data_table)
        self.resize(500, 700)
