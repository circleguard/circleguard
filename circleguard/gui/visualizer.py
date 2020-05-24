from PyQt5.QtGui import QIcon
from circlevis import Visualizer

from utils import resource_path
from settings import get_setting

class CGVisualizer(Visualizer):
    def __init__(self, beatmap_info, replays=[], events=[], library=None):
        speeds = get_setting("speed_options")
        start_speed = get_setting("default_speed")
        paint_info = get_setting("visualizer_info")
        super().__init__(beatmap_info, replays, events, library, speeds, start_speed, paint_info)
        self.setWindowIcon(QIcon(resource_path("logo/logo.ico")))
