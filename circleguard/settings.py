import re
import os

# pylint: disable=no-name-in-module
from PyQt5.QtCore import QSettings, QStandardPaths
# pylint: enable=no-name-in-module
from packaging import version
# it's tempting to use QSettings builtin ini file support instead of configparser,
# but that doesn't let us write comments, which is rather important to explain
# what attributes are available through string formatting.
from configparser import ConfigParser

from utils import resource_path
from version import __version__


DEFAULTS = {
    "Locations": {
        "cache_location": QStandardPaths.writableLocation(QStandardPaths.AppDataLocation) + "/cache.db",
        "log_dir": QStandardPaths.writableLocation(QStandardPaths.AppDataLocation) + "/logs/"
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
        "cache_location",
        "log_dir"
    ]
}

SETTINGS = QSettings("Circleguard", "Circleguard")
# see third bullet here https://doc.qt.io/qt-5/qsettings.html#platform-limitations,
# we don't want the global keys on macos when calling allkeys
SETTINGS.setFallbacksEnabled(False)

# assemble dict of {key: [type, section]} since we have nested dicts in DEFAULTS
# double list comprehension feels sooo backwards to write
TYPES = {k:[type(v), section] for section,d in DEFAULTS.items() for k,v in d.items()}
CFG_PATH = resource_path("circleguard.cfg")

def overwrite_outdated_settings():
    last_version = version.parse(get_setting("last_version"))
    last_version = version.parse(last_version.base_version)  # remove dev stuff
    for ver, changed_arr in CHANGED.items():
        if last_version < version.parse(ver):
            for setting in changed_arr:
                update_default(setting, DEFAULTS[TYPES[setting][1]][setting])
    update_default("last_version", __version__)


def overwrite_with_config_settings():
    config = ConfigParser(interpolation=None)
    config.read(resource_path("circleguard.cfg"))
    for section in config.sections():
        for k in config[section]:
            type_ = TYPES[k][0]
            if type_ is bool:
                val = config.getboolean(section, k)
            elif type_ is int:
                val = config.getint(section, k)
            else:
                val = config.get(section, k)
            update_default(k, val)


def reset_defaults():
    SETTINGS.clear()
    for d in DEFAULTS.values():
        for key,value in d.items():
            SETTINGS.setValue(key, value)
    SETTINGS.sync()


def get_setting(name):
    type_ = TYPES[name][0]
    val = SETTINGS.value(name)
    # windows registry keys doesnt properly preserve types, so convert "false"
    # keys to a true False value instead of bool("false") which would return True.
    # second bullet here: https://doc.qt.io/qt-5/qsettings.html#platform-limitations
    if type_ is bool:
        return False if val in ["false", "False"] else bool(val)
    v = type_(SETTINGS.value(name))
    return v


def update_default(name, value):
    # import traceback
    # import sys
    # traceback.print_stack(file=sys.stdout)
    SETTINGS.setValue(name, TYPES[name][0](value))

# overwrites circleguard.cfg with our settings
def overwrite_config():
    config = ConfigParser(allow_no_value=True, interpolation=None)
    for section in DEFAULTS.keys():
        config[section] = {}
    for key in SETTINGS.allKeys():
        if key not in TYPES:
            continue
        config[TYPES[key][1]][key] = str(SETTINGS.value(key))

    with open(CFG_PATH, "w+") as f:
        config.write(f)

# add setting if missing (occurs between updates if we add a new default setting)
for d in DEFAULTS.values():
    for key,value in d.items():
        if not SETTINGS.contains(key):
            SETTINGS.setValue(key, value)

# create cfg file if it doesn't exist
if not os.path.exists(CFG_PATH):
    overwrite_config()

# overwrite our settings with the config settings (if the user changed them while
# the application was closed)
overwrite_with_config_settings()

# overwrite setting key if they were changed in a release
# has to be called after overwrite_with_config_settings or the file will
# overwrite our changes here since it's not synced to the file
overwrite_outdated_settings()

if not get_setting("ran"):
    reset_defaults()
