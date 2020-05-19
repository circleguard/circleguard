from PyQt5.QtGui import QIcon
from circlevis import Visualizer

from utils import resource_path

class CGVisualizer(Visualizer):
    def __init__(self, beatmap_info, replays=[], events=[], library=None, speeds=[1], start_speed=1, paint_info=True):
        super().__init__(beatmap_info, replays, events, library, speeds, start_speed, paint_info)
        self.setWindowIcon(QIcon(resource_path("logo/logo.ico")))
