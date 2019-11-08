from pathlib import Path
import sys
import os
from datetime import datetime, timedelta

from packaging import version
import requests

# placeholder imports to have all imports at the top of the file. Imported for
# real farther below
#from settings import get_setting
#from version import __version__

# placed above local imports to avoid circular import errors
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


from settings import get_setting
from version import __version__


def run_update_check():
    last_check = datetime.strptime(get_setting("last_update_check"), get_setting("timestamp_format"))
    next_check = last_check + timedelta(hours=1)
    if not next_check < datetime.now():
        return get_idle_setting_str()
    try:
        # check for new version
        git_request = requests.get("https://api.github.com/repos/circleguard/circleguard/releases/latest").json()
        git_version = version.parse(git_request["name"])
        set_setting("latest_version", git_version)
        set_setting("last_update_check", datetime.now().strftime(get_setting("timestamp_format")))
    except:
        # user is propably offline
        pass
    return get_idle_setting_str()


def get_idle_setting_str():
    current_version = version.parse(__version__)
    if current_version < version.parse(get_setting("latest_version")):
        return "<a href=\'https://circleguard.dev/download'>Update available!</a>"
    else:
        return "Idle"

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
