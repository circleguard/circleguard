# pylint: disable=no-name-in-module
from PyQt5.QtCore import QSettings, QStandardPaths
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
    "cache_location": QStandardPaths.writableLocation(QStandardPaths.AppDataLocation) + "/cache.db",
    "log_save": True,
    "log_dir": "./logs/",
    "log_mode": 1, # ERROR
    "log_output": 1, # TERMINAL
    "local_replay_dir": "./examples/replays/",
    "visualizer_info": True,
    "visualizer_bg": False,
    # string settings
    "message_loading_replays": "[{ts:%X}] Loading {num_replays} Replays on map {map_id}",
    "message_ratelimited": "[{ts:%X}] Ratelimited, waiting for {s} seconds",
    "message_starting_comparing": "[{ts:%X}] Comparing Replays",
    "message_finished_comparing": "[{ts:%X}] Done",
    # it is possible though extremely unusual for the replays to have different map ids. This is good enough
    "message_cheater_found": "[{ts:%X}] {similarity:.1f} similarity. {r1.username} vs {r2.username} on map {r1.map_id}, {r.later_replay.username} set later. Extremely similar replays; look at the visualization to investigate further.",
    "message_no_cheater_found": "[{ts:%X}] {similarity:.1f} similarity. {r1.username} vs {r2.username} on map {r1.map_id}. Replays likely not stolen.",

    "string_result_text": "[{ts:%x %H:%M}] {similarity:.1f} similarity. {r.later_replay.username} (set later) vs {r.earlier_replay.username} on map {r1.map_id}",
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
}

CHANGED = {
    "1.1.0": [
        "message_cheater_found",
        "message_no_cheater_found",
        "string_result_text"
    ],
    "1.2.0": [
        "message_loading_replays"
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
    # windows registry keys doesnt properly preserve types, so convert "false"
    # keys to a true False value instead of bool("false") which would return True.
    # second bullet here: https://doc.qt.io/qt-5/qsettings.html#platform-limitations
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
