from pathlib import Path
import sys
import os

ROOT_PATH = Path(__file__).parent.absolute()

def resource_path(str_path):
    """
    Returns a Path representing where to look for resource files for the program,
    such as databases or images.

    This location changes if the program is run from an application built with pyinstaller.
    """

    if hasattr(sys, '_MEIPASS'):  # being run from a pyinstall'd app
        return Path(sys._MEIPASS) / Path(str_path)  # pylint: disable=no-member
    return ROOT_PATH / Path(str_path)


class Run():
    """
    Stores all the information needed to recreated or represent a run.
    Tab-specific information is found in subclasses.
    """

    def __init__(self, run_id, event):
        self.run_id = run_id
        self.event = event


class MapRun(Run):

    def __init__(self, run_id, event, map_id, user_id, num, thresh):
        super().__init__(run_id, event)
        self.map_id = map_id
        self.user_id = user_id
        self.num = num
        self.thresh = thresh

class ScreenRun(Run):
    def __init__(self, run_id, event, user_id, num_top, num_users, thresh):
        super().__init__(run_id, event)
        self.user_id = user_id
        self.num_top = num_top
        self.num_users = num_users
        self.thresh = thresh

class LocalRun(Run):
    def __init__(self, run_id, event, path, map_id, user_id, num, thresh):
        super().__init__(run_id, event)
        self.path = path
        self.map_id = map_id
        self.user_id = user_id
        self.num = num
        self.thresh = thresh

class VerifyRun(Run):
    def __init__(self, run_id, event, map_id, user_id_1, user_id_2, thresh):
        super().__init__(run_id, event)
        self.map_id = map_id
        self.user_id_1 = user_id_1
        self.user_id_2 = user_id_2
        self.thresh = thresh
