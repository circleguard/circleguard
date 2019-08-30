import re
import os

# pylint: disable=no-name-in-module
from PyQt5.QtCore import QSettings, QStandardPaths
# pylint: enable=no-name-in-module
from packaging import version
from configparser import RawConfigParser

from utils import resource_path
from version import __version__


DEFAULTS = {
    "Locations": {
        "cache_location": QStandardPaths.writableLocation(QStandardPaths.AppDataLocation) + "/cache.db",
        "log_dir": "./logs/"
    },
    "Messages": {
        "message_loading_replays": "[{ts:%X}] Loading {num_replays} Replays on map {map_id}",
        "message_ratelimited": "[{ts:%X}] Ratelimited, waiting for {s} seconds",
        "message_starting_comparing": "[{ts:%X}] Comparing Replays",
        "message_finished_comparing": "[{ts:%X}] Done",
        # it is possible though extremely unusual for the replays to have different map ids. This is good enough
        "message_cheater_found": "[{ts:%X}] {similarity:.1f} similarity. {r1.username} vs {r2.username} on map {r1.map_id}, {r.later_replay.username} set later. Extremely similar replays; look at the visualization to investigate further.",
        "message_no_cheater_found": "[{ts:%X}] {similarity:.1f} similarity. {r1.username} vs {r2.username} on map {r1.map_id}. Replays likely not stolen."
    },
    "Strings": {
        "string_result_text": "[{ts:%x %H:%M}] {similarity:.1f} similarity. {r.later_replay.username} (set later) vs {r.earlier_replay.username} on map {r1.map_id}",
    },
    "Templates": {
        "template_replay_steal": ("[osu!std] {r.later_replay.username} | Replay Stealing"
                             "\n\n"
                             "Profile: https://osu.ppy.sh/users/{r.later_replay.user_id}"
                             "\n\n"
                             "Map: https://osu.ppy.sh/b/{r.later_replay.map_id}"
                             "\n\n"
                             "{r.later_replay.username}'s replay (cheated): https://osu.ppy.sh/scores/osu/{r.later_replay.replay_id}/download"
                             "\n\n"
                             "{r.earlier_replay.username}'s replay (original): https://osu.ppy.sh/scores/osu/{r.earlier_replay.replay_id}/download"
                             "\n\n"
                             "{r.similarity:.2f} similarity according to [circleguard](https://github.com/circleguard/circleguard) (higher is less similar)")
    },
    "Thresholds": {
        "threshold_cheat": 18,
        "threshold_display": 25
    },
    "Appearance": {
        "dark_theme": False,
        "visualizer_info": True,
        "visualizer_bg": False
    },
    "Experimental": {
        "rainbow_accent": False
    },
    "Logs": {
        "log_save": True,
        "log_mode": 1, # ERROR
        "log_output": 1 # TERMINAL
    },
    "Core": {
        "ran": False,
        "last_version": "0.0.0",  # force run update_settings if the user previously had a version without this key
        "api_key": ""
    },
    "Caching": {
        "caching": True
    }
}

# it's tempting to use QSettings builtin ini file support, but that doesn't let us write comments,
# which is rather important to explain what attributes are available through string formatting.
config = RawConfigParser(allow_no_value=True)
CFG_PATH = resource_path("circleguard.cfg")
# create cfg file if it doesn't exist
if not os.path.exists(CFG_PATH):
    for section,d in DEFAULTS.items():
        config.add_section(section)
        for k,v in d.items():
            config.set(section, k, v)
    with open(CFG_PATH, "w+") as f:
        config.write(f)

config.read(resource_path("circleguard.cfg"))


# TODO
# try using Qsettings("pathtoinifile.cfg", QFormat.INI or whatever) to
# write and read the ini file. It should still be relatively human readable to change

# PROBLEM: cant use comments with qsettings since the file is only meant to be
# read/write with respect to qt and not end users or other apps. Solution?
# use python configparser I guess.

CHANGED = {
    "1.1.0": [
        "message_cheater_found",
        "message_no_cheater_found",
        "string_result_text"
    ],
    "1.2.0": [
        "message_loading_replays"
    ],
    "1.3.0": [
        "cache_location"
    ]
}

SETTINGS = QSettings("Circleguard", "Circleguard")
# assemble dict of {key: [type, section]} since we have nested dicts in DEFAULTS
# double list comprehension feels sooo backwards to write
TYPES = {k:[type(v), section] for section,d in DEFAULTS.items() for k,v in d.items()}

def overwrite_outdated_settings():
    last_version = version.parse(get_setting("last_version"))
    last_version = version.parse(last_version.base_version)  # remove dev stuff
    for ver, changed_arr in CHANGED.items():
        if last_version < version.parse(ver):
            for setting in changed_arr:
                update_default(setting, DEFAULTS[TYPES[setting][1]][setting])
    update_default("last_version", __version__)


def reset_defaults():
    SETTINGS.clear()
    for d in DEFAULTS.values():
        for key,value in d.items():
            SETTINGS.setValue(key, value)
    SETTINGS.sync()

if not SETTINGS.contains("ran"):
    reset_defaults()


def get_setting(name):
    type_ = TYPES[name][0]
    val = SETTINGS.value(name)
    # windows registry keys doesnt properly preserve types, so convert "false"
    # keys to a true False value instead of bool("false") which would return True.
    # second bullet here: https://doc.qt.io/qt-5/qsettings.html#platform-limitations
    if type_ is bool:
        return False if val == "false" else bool(val)
    v = type_(SETTINGS.value(name))
    return v


def update_default(name, value):
    SETTINGS.setValue(name, TYPES[name][0](value))


# add setting if missing (occurs between updates if we add a new default setting)
for d in DEFAULTS.values():
    for key,value in d.items():
        if not SETTINGS.contains(key):
            SETTINGS.setValue(key, value)

# overwrite setting key if they were changed in a release
overwrite_outdated_settings()
