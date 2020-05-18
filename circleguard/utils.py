# this is named ``gui_utils`` and not ``utils`` to prevent collision with
# ``circleguard.utils`` (not our circleguard, but circlecore, which is on pip as
# circleguard). Yes this is bad. But it works.

from pathlib import Path
import sys
import os
from datetime import datetime, timedelta

from circleguard import Mod
from packaging import version
import requests
from requests import RequestException
from PyQt5.QtWidgets import QLayout

# placeholder imports to have all imports at the top of the file. Imported for
# real farther below
#from settings import get_setting, set_setting
#from version import __version__

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


from settings import get_setting, set_setting
from version import __version__


def run_update_check():
    last_check = datetime.strptime(get_setting("last_update_check"), get_setting("timestamp_format"))
    next_check = last_check + timedelta(hours=1)
    if next_check > datetime.now():
        return get_idle_setting_str()
    try:
        # check for new version
        git_request = requests.get("https://api.github.com/repos/circleguard/circleguard/releases/latest").json()
        git_version = version.parse(git_request["name"])
        set_setting("latest_version", git_version)
        set_setting("last_update_check", datetime.now().strftime(get_setting("timestamp_format")))
    except RequestException:
        # user is probably offline
        pass
    return get_idle_setting_str()


def get_idle_setting_str():
    current_version = version.parse(__version__)
    if current_version < version.parse(get_setting("latest_version")):
        return "<a href=\'https://circleguard.dev/download'>Update available!</a>"
    else:
        return "Idle"


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


class Run():
    """
    Represents a click of the Run button on the Main tab, which can contain
    multiple Checks, each of which contains a set of Loadables.
    """

    def __init__(self, checks, run_id, event):
        self.checks = checks
        self.run_id = run_id
        self.event = event


class Player():
    def __init__(self, replay, pen):
        self.pen = pen
        self.username = replay.username
        self.t = replay.t
        # copy so we don't flip the actual replay's xy coordinates when we
        # account for hr (not doing this causes replays to be flipped on odd
        # runs of the visualizer and correct on even runs of the visualizer)
        self.xy = replay.xy.copy()
        self.k = replay.k
        self.end_pos = 0
        self.start_pos = 0
        self.mods = replay.mods

class BeatmapInfo():
    """
    Represents the information necessary to load a beatmap.

    Notes
    -----
    If multiple ways to load a beatmap are known, all ways should be provided so
    consumers can choose the order of ways to load the beatmap.

    If one way to load a beatmap is *not* available, it should be left as
    ``None``.
    """

    def __init__(self, *, map_id=None, path=None):
        self.map_id = map_id
        self.path = path

    def available(self):
        """
        Whether this beatmap can be loaded with the information we have or not.
        """
        return bool(self.map_id) or bool(self.path)
