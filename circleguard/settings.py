# pylint: disable=no-name-in-module
from PyQt5.QtCore import QSettings
# pylint: enable=no-name-in-module
import re
from version import __version__

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


def _version_to_int(version):
    version = version.split(".")
    version = [re.sub("[^0-9]", "", digit) for digit in version]
    version = int("".join(version))
    return version


def update_settings():
    old_version = _version_to_int(get_setting("last_version"))
    current_version = _version_to_int(__version__)
    for change_key, change_array in CHANGED.items():
        if _version_to_int(change_key) < current_version:
            for setting in change_array:
                SETTINGS.setValue(setting, DEFAULTS[setting])
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
    return type(DEFAULTS[name])(SETTINGS.value(name))


def update_default(name, value):
    SETTINGS.setValue(name, type(DEFAULTS[name])(value))


# add setting if missing (occurs between updates if we add a new default setting)
for key, value in DEFAULTS.items():
    if not SETTINGS.contains(key):
        SETTINGS.setValue(key, value)

# reset setting key if updated
update_settings()