from pathlib import Path
import sys
import os
from datetime import datetime, timedelta

import numpy as np
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
ROOT_PATH = Path(__file__).parent.absolute()
def resource_path(str_path):
    """
    Returns a Path representing where to look for resource files for the program,
    such as databases or images.

    This location changes if the program is run from an application built with pyinstaller.
    """

    if hasattr(sys, '_MEIPASS'): # being run from a pyinstall'd app
        return Path(sys._MEIPASS) / Path(str_path) # pylint: disable=no-member
    return ROOT_PATH / Path(str_path)


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

class InvalidModException(Exception):
    """
    We were asked to parse an invalid mod string.
    """

def parse_mod_string(mod_string):
    """
    Takes a string made up of two letter mod names and converts them
    to a circlecore ModCombination.

    Returns None if the string is empty (mod_string == "")
    """
    if mod_string == "":
        return None
    if len(mod_string) % 2 != 0:
        raise InvalidModException(f"Invalid mod string {mod_string} (not of even length)")
    # slightly hacky, using ``Mod.NM`` our "no mod present" mod
    mod = Mod.NM
    for i in range(2, len(mod_string) + 1, 2):
        single_mod_string = mod_string[i - 2: i]
        # there better only be one Mod that has an acronym matching ours, but a comp + 0 index works too
        matching_mods = [mod for mod in Mod.ORDER if mod.short_name() == single_mod_string]
        if not matching_mods:
            raise InvalidModException(f"Invalid mod string (no matching mod found for {single_mod_string})")
        mod += matching_mods[0]
    return mod


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


class Player:
    def __init__(self, replay, cursor_color):
        self.cursor_color = cursor_color
        self.username = replay.username
        self.t = replay.t
        # copy so we don't flip the actual replay's xy coordinates when we
        # account for hr (not doing this causes replays to be flipped on odd
        # runs of the visualizer and correct on even runs of the visualizer)
        self.xy = np.copy(replay.xy)
        self.k = replay.k
        self.end_pos = 0
        self.start_pos = 0
        self.mods = replay.mods
