# pylint: disable=no-name-in-module
from PyQt5.QtCore import QSettings
# pylint: enable=no-name-in-module

DEFAULTS = {
    "ran": False,
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
    "message_cheater_found": "[{ts:%X}] {similarity:.1f} similarity. {replay1_name} vs {replay2_name}, {later_name} set later. Extremely similar replays; you just caught yourself a cheater.",
    "message_no_cheater_found": "[{ts:%X}] {similarity:.1f} similarity. {replay1_name} vs {replay2_name}. Replays likely not stolen.",

    "string_result_text": "[{ts:%x} {ts:%H}:{ts:%M}] {similarity:.1f} similarity. {replay1_name} vs {replay2_name}"
}


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
    SETTINGS.setValue(name, type(DEFAULTS[name](value)))


# add setting if missing (occurs between updates if we add a new default setting)
for key, value in DEFAULTS.items():
    if not SETTINGS.contains(key):
        SETTINGS.setValue(key, value)
