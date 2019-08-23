from pathlib import Path
import sys
import os

from settings import get_setting

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


def write_log(message):
    log_dir = resource_path(get_setting("log_dir"))
    if not os.path.exists(log_dir):  # create dir if nonexistent
        os.makedirs(log_dir)
    directory = os.path.join(log_dir, "circleguard.log")
    with open(directory, 'a+') as f:  # append so it creates a file if it doesn't exist
        f.seek(0)
        data = f.read().splitlines(True)
    data.append(message+"\n")
    with open(directory, 'w+') as f:
        f.writelines(data[-10000:])  # keep file at 10000 lines

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
