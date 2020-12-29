from PyQt5.QtGui import QIcon

from utils import resource_path
from settings import get_setting

# necessary to avoid loading circlevis
def get_visualizer():
    from circlevis import Visualizer
    class CGVisualizer(Visualizer):
        def __init__(self, beatmap_info, replays=[], events=[], library=None):
            speeds = get_setting("speed_options")
            start_speed = get_setting("default_speed")
            snaps_args = {"only_on_hitobjs": get_setting("ignore_snaps_off_hitobjs")}

            super().__init__(beatmap_info, replays, events, library, speeds, start_speed, snaps_args=snaps_args)
            self.setWindowIcon(QIcon(resource_path("logo/logo.ico")))

    return CGVisualizer
