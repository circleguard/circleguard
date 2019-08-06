# pylint: disable=no-name-in-module
from PyQt5.QtCore import QSettings
# pylint: enable=no-name-in-module
import re
from version import __version__
from packaging import version

DEFAULTS = {
    "ran": False,
    "last_version": "0.0.0",  # force run update_settings if the user previously had a version without this key
    "threshold_cheat": 18,
    "threshold_display": 25,
    "api_key": "",
    "dark_theme": False,
    "rainbow_accent": False,
    "caching": True,
    "cache_dir": "./db/",
    "log_save": True,
    "log_dir": "./logs/",
    "log_mode": 1, # ERROR
    "log_output": 1, # TERMINAL
    "local_replay_dir": "./examples/replays/",
    # string settings
    "message_loading_replays": "[{ts:%X}] Loading {num_replays} Replays",
    "message_starting_comparing": "[{ts:%X}] Comparing Replays",
    "message_finished_comparing": "[{ts:%X}] Done",
    # it is possible though extremely unusual for the replays to have different map ids. This is good enough
    "message_cheater_found": "[{ts:%X}] {similarity:.1f} similarity. {r1.username} vs {r2.username} on map {r1.map_id}, {later_name} set later. Extremely similar replays; likely a cheated replay.",
    "message_no_cheater_found": "[{ts:%X}] {similarity:.1f} similarity. {r1.username} vs {r2.username} on map {r1.map_id}. Replays likely not stolen.",

    "string_result_text": "[{ts:%x} {ts:%H}:{ts:%M}] {similarity:.1f} similarity. {r1.username} vs {r2.username} on map {r1.map_id}"
}

CHANGED = {
    "1.1.0": [
        "message_cheater_found",
        "message_no_cheater_found",
        "string_result_text"
    ]
}


def overwrite_outdated_settings():
    last_version = version.parse(get_setting("last_version"))
    last_version = version.parse(last_version.base_version)  # remove dev stuff
    for ver, changed_arr in CHANGED.items():
        if last_version < version.parse(ver):
            for setting in changed_arr:
                update_default(setting, DEFAULTS[setting])
    update_default("last_version", __version__)


def reset_defaults():
    SETTINGS.clear()
    for key, value in DEFAULTS.items():
        SETTINGS.setValue(key, value)
    SETTINGS.sync()


SETTINGS = QSettings("Circleguard", "Circleguard")
if not SETTINGS.contains("ran"):
    reset_defaults()


def get_setting(name):
    type_ = type(DEFAULTS[name])
    val = SETTINGS.value(name)
    if type_ is bool:
        return False if val == "false" else bool(val)
    return type(DEFAULTS[name])(SETTINGS.value(name))


def update_default(name, value):
    SETTINGS.setValue(name, type(DEFAULTS[name])(value))


# add setting if missing (occurs between updates if we add a new default setting)
for key, value in DEFAULTS.items():
    if not SETTINGS.contains(key):
        SETTINGS.setValue(key, value)

# overwrite setting key if they were changed in a release
overwrite_outdated_settings()
