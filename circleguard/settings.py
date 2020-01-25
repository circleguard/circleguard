import re
import os
from pathlib import Path
from datetime import datetime, timedelta
import abc

# pylint: disable=no-name-in-module
from PyQt5.QtCore import QSettings, QStandardPaths, pyqtSignal, QObject
# pylint: enable=no-name-in-module
from packaging import version
# it's tempting to use QSettings builtin ini file support instead of configparser,
# but that doesn't let us write comments, which is rather important to explain
# what attributes are available through string formatting.
from configparser import ConfigParser

from utils import resource_path
from version import __version__

COMMENTS = {
    "file": "Please read the following before editing this file.\n"
            "We do not validate or error check these settings, so if you put an incorrect value or syntax, your application will crash on start.\n"
            "If this occurs, you can either fix the error, or if you can't find the cause, delete the file entirely.\n"
            "This will cause a fresh config to be created when circleguard is run again.\n"
            "In places where it is easy to cause issues by editing the settings, we will warn you about it.\n"
            "Some settings use curly braces `{}`, especially the Messages, Strings, and Templates sections.\n"
            "These denote settings to be filled with python's strformat. We do not currently document what variables are passed to you through strformat for each setting.\n"
            "The `ts` seen in many of the settings is a datetime.datetime object, representing the timestamp at that time.\n"
            "You may of course use any formatting directive in the settings (instead of the default %X) that datetime supports.\n\n"
            "After you change settings, you must press the \"sync\" button on the settings tab for them to take effect.\n\n"
            "This file may be edited without Circleguard being open. Any changes will take effect the next time you open Circleguard.",
    "Locations": {
        "section": "The path to various file or directories used by the program",
        "cache_location": "Where the cache to read and write replays to is.\n"
                "If this location doesn't exist, it will be created, including any nonexistent directories in the path",
        "config_location": "Where the circelguard.cfg file (this very file) resides",
        "log_dir": "Where to write logs. We currently use a single log file (circleguard.log), but the setting is a directory to allow for future expansion"
    },
    "Messages": {
        "section": "Messages written to the terminal (the text box at the bottom of the Main tab) at various times",
        "message_loading_replays": "Displayed when we begin loading replays",
        "message_ratelimited": "Displayed when the api key gets ratelimited",
        "message_starting_investigation": "Displayed when we start to investigate the loaded replays",
        "message_finished_investigation": "Displayed when we have finished investigating all replays",
        "message_steal_found": "Displayed when an investigation for replay stealing has a similarity below Thresholds/steal_max_sim",
        "message_steal_found_display": "Displayed when an investigation for replay stealing has a similarity below Thresholds/steal_max_sim_display",
        "message_relax_found": "Displayed when an investigation for relax has a ur below Thresholds/relax_max_ur",
        "message_relax_found_display": "Displayed when an investigation for relax has a ur below Thresholds/relax_max_ur_display",
        "message_correction_found": "Displayed when an investigation for aim correction satisfies both Thresholds/correction_max_angle and correction_min_distance",
        "message_correction_found_display": "Displayed when an investigation for aim correction satisfies both Thresholds/correction_max_angle_display and correction_min_distance_display",
        "message_correction_snaps": "How to represent a snap for aim correction. The result is passed to message_correction_found and message_correction_found_display as `snaps`"
    },
    "Strings": {
        "section": "Labels seen on various widgets",
        "string_result_steal": "Displayed on the Results tab for a replay stealing result",
        "string_result_relax": "Displayed on the Results tab for a relax result",
        "string_result_correction": "Displayed on the Results tab for an aim correction result"
    },
    "Templates": {
        "section": "The templates that are copied to your clipboard from the Results tab \"copy template\" button",
        "template_steal": "Available for copying for replay stealing results",
        "template_relax": "Available for copying for relax results",
        "template_correction": "Available for copying for aim correction results"
    },
    "Thresholds": {
        "section": "Thresholds for when to store results and when to display results for various types of cheats.\n"
                "Although possible to set _display settings lower than their respective _cheat setting, it is not advised",
        "steal_max_sim": "The max similarity for a replay stealing comparison to be counted as cheated",
        "steal_max_sim_display": "The max similarity for a replay stealing comparison to be printed to the terminal",
        "relax_max_ur": "The max ur for a replay to be counted as cheated",
        "relax_max_ur_display": "The max ur for a replay to be printed to the terminal",
        "correction_max_angle": "For any thee points in a replay, if the angle between them (in degrees) is smaller than this value, the points are counted as a Snap (indicative of aim correction). Note that the three points must also satisfy correction_min_distance",
        "correction_max_angle_display": "Unused. Aim Correction does not currently have display options",
        "correction_min_distance": "For any three points A B C in a replay, if the distance between AB or BC is greater than this value, the points are counted as a Snap (indicative of aim correction). Note that the three points must also satisfy correction_max_angle",
        "correction_min_distance_display": "Unused. Aim Correction does not currently have display options"
    },
    "Appearance": {
        "dark_theme": "If True, uses a dark theme for the application",
        "visualizer_info": "If True, info about the players is displayed on the visualizer",
        "visualizer_black_bg": "If True, uses a pure black background for the visualizer. Otherwise uses the background of the current theme",
        "required_style": "The css to apply to a widget if it is required to be filled in to complete an action. This is applied if a required field in a Loadable is empty when you click run, for instance"
    },
    "Experimental": {
        "section": "These settings are liable to be resource-intensive, behave in unexpected ways, or haven't been tested fully yet. Proceed at your own risk",
        "rainbow_accent": "Makes the accent color (defines the color of the highlight around the currently focused widget, among other things) constantly cycle through colors"
    },
    "Logs": {
        "log_save": "Whether to save logs to a file (whose path is defined by Locations/log_dir)",
        "log_mode": "All logs with a severity level at or higher than this value will be outputted.\n"
                "Critical: 0\n"
                "Error: 1\n"
                "Warning: 2\n"
                "Info: 3\n"
                "Debug: 4\n"
                "Trace: 5",
        "log_output": "Where to output logs. This setting has no relation to log_save, so if log_output is 0 and log_save is True, logs will still be written to the log file at the level defined by log_mode.\n"
                "Nowhere: 0\n"
                "Terminal: 1\n"
                "Debug Window: 2\n"
                "Terminal and Debug Window: 3"
    },
    "Core": {
        "section": "Internal settings. Don't modify unless you've been told to, or know exactly what you're doing",
        "ran": "Whether Circleguard has been run on this system before. If False when Circleguard is launched, all settings will be reset to their default and the wizard will be displayed",
        "last_version": "The most recent version of Circleguard run on this system. Used to overwrite settings when they change between versions",
        "api_key": "The api key to use in circlecore",
        "timestamp_format": "The format of last_update_check",
        "last_update_check": "The last time we checked for a new version. Only checks once every hour",
        "latest_version": "The latest Circleguard version available on github"
    },
    "Caching": {
        "caching": "Whether to cache downloaded replays to a file (whose path is defined by Locations/cache_location)"
    }
}

class LinkableSetting():
    """
    XXX IMPLEMENTATION NOTE FOR SUBCLASSES:
    all python classes must come before c classes (like QWidget) or super calls break.
    Further reading: https://www.riverbankcomputing.com/pipermail/pyqt/2017-January/038650.html

    eg, def MyClass(LinkableSetting, QFrame) NOT def MyClass(QFrame, LinkableSetting)
    """
    registered_classes = []
    def __init__(self, setting):
        self.setting = setting
        self.registered_classes.append(self)
        self.setting_value = get_setting(setting)

    @abc.abstractmethod
    def on_setting_changed(self, new_value):
        """
        Called when the internal setting this class is linked to is changed, from
        a source other than this class. An extremely common use case - and the
        intended one - is to change the value of a slider/label/other widget to
        reflect the new setting value, so all settings are in sync (gui and internal).
        """
        pass

    def filter(self, setting_changed):
        """
        A predicate that returns true if this class should accept signals when the given
        setting is changed (signals in the form of a call to on_setting_changed)
        """
        return self.setting == setting_changed

    def on_setting_changed_from_gui(self, value):
        """
        Called when our setting is changed from the gui,
        and our internal settings need to be updated to reflect that.
        """
        set_setting(self.setting, value)

DEFAULTS = {
    "Locations": {
        "cache_location": QStandardPaths.writableLocation(QStandardPaths.AppDataLocation) + "/cache.db",
        "log_dir": QStandardPaths.writableLocation(QStandardPaths.AppDataLocation) + "/logs/",
        "config_location": QStandardPaths.writableLocation(QStandardPaths.AppDataLocation) + "/circleguard.cfg"
    },
    "Messages": {
        "message_loading_replays":         "[{ts:%X}] Loading {num_unloaded} of {num_total} replays",
        "message_ratelimited":             "[{ts:%X}] Ratelimited, waiting for {s} seconds",
        "message_starting_investigation":  "[{ts:%X}] Running {check_type} check",
        "message_finished_investigation":  "[{ts:%X}] Done",
        # it is possible though extremely unusual for the replays to have different map ids. This is good enough
        # replay.mods.short_name is a function, not an attribute, and we can't call functions in format strings. We need to pass mods_short_name and mods_long_name in addition to replay1 and replay2
        "message_steal_found":              "[{ts:%X}] {sim:.1f} similarity. {replay1.username} +{replay1_mods_short_name} vs {replay2.username} +{replay2_mods_short_name} on map {replay1.map_id}, {r.later_replay.username} set later",
        "message_steal_found_display":      "[{ts:%X}] {sim:.1f} similarity. {replay1.username} +{replay1_mods_short_name} vs {replay2.username} +{replay2_mods_short_name} on map {replay1.map_id}, {r.later_replay.username} set later. Not below threshold",
        "message_relax_found":              "[{ts:%X}] {ur:.1f} ur. {replay.username} +{mods_short_name} on map {replay.map_id}",
        "message_relax_found_display":      "[{ts:%X}] {ur:.1f} ur. {replay.username} +{mods_short_name} on map {replay.map_id}. Not below threshold",
        "message_correction_found":         "[{ts:%X}] {replay.username} +{mods_short_name} on map {replay.map_id}. Snaps:\n{snaps}",
        "message_correction_found_display": "[{ts:%X}] {replay.username} +{mods_short_name} on map {replay.map_id}. Snaps:\n{snaps}",
        # have to use a separate message here because we can't loop in ``.format`` strings, can only loop in f strings which only work in a
        # local context and aren't usable for us. Passed as ``snaps=snaps`` in message_correction_found, once formatted. Each snap formats
        # this setting and does a ``"\n".join(snap_message)`` to create ``snaps``.
        "message_correction_snaps":         "Time (ms): {time:.0f}\tAngle (deg): {angle:.2f}\tDistance (px): {distance:.2f}"

    },
    "Strings": {
        "string_result_steal":       "[{ts:%x %H:%M}] {similarity:.1f} similarity. {r.later_replay.username} +{replay1_mods_short_name} (set later) vs {r.earlier_replay.username} +{replay2_mods_short_name} on map {r1.map_id}",
        "string_result_relax":       "[{ts:%x %H:%M}] {ur:.1f} ur. {replay.username} +{mods_short_name} on map {replay.map_id}",
        "string_result_correction":  "[{ts:%x %H:%M}] {replay.username} +{mods_short_name} on map {replay.map_id}"
    },
    "Templates": {
        "template_steal":      ("[osu!std] {r.later_replay.username} | Replay Stealing"
                                "\n\n"
                                "Profile: https://osu.ppy.sh/users/{r.later_replay.user_id}"
                                "\n\n"
                                "Map: https://osu.ppy.sh/b/{r.later_replay.map_id}"
                                "\n\n"
                                "{r.later_replay.username}'s replay (cheated): https://osu.ppy.sh/scores/osu/{r.later_replay.replay_id}/download"
                                "\n\n"
                                "{r.earlier_replay.username}'s replay (original): https://osu.ppy.sh/scores/osu/{r.earlier_replay.replay_id}/download"
                                "\n\n"
                                "{r.similarity:.2f} similarity according to [circleguard](https://github.com/circleguard/circleguard) (higher is less similar)"),
        "template_relax":      ("[osu!std] {r.replay.username} | Relax"
                                "\n\n"
                                "Profile: https://osu.ppy.sh/users/{r.replay.user_id}"
                                "\n\n"
                                "Map: https://osu.ppy.sh/b/{r.replay.map_id}"
                                "\n\n"
                                "replay download: https://osu.ppy.sh/scores/osu/{r.replay.replay_id}/download"
                                "\n\n"
                                "ur (ucv): {r.ur:.2f} according to [circleguard](https://github.com/circleguard/circleguard)"),
        "template_correction": ("[osu!std] {r.replay.username} | Aim Correction"
                                "\n\n"
                                "Profile: https://osu.ppy.sh/users/{r.replay.user_id}"
                                "\n\n"
                                "Map: https://osu.ppy.sh/b/{r.replay.map_id}"
                                "\n\n"
                                "replay download: https://osu.ppy.sh/scores/osu/{r.replay.replay_id}/download"
                                "\n\n"
                                "Snaps according to [circleguard](https://github.com/circleguard/circleguard):"
                                "\n\n"
                                "{snap_table}")
    },
    "Thresholds": {
        "steal_max_sim": 18,
        "steal_max_sim_display": 25,
        "relax_max_ur": 50,
        "relax_max_ur_display": 90,
        "correction_max_angle": 10,
        "correction_max_angle_display": 10,
        "correction_min_distance": 8,
        "correction_min_distance_display": 8
    },
    "Appearance": {
        "dark_theme": False,
        "visualizer_info": True,
        "visualizer_black_bg": False,
        "required_style": "QLineEdit { border: 1px solid red }\n"
                          "WidgetCombiner { border: 1px solid red }"
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
        "api_key": "",
        "timestamp_format": "%H:%M:%S %m.%d.%Y",
        "last_update_check": "00:00:00 01.01.1970", # aka datetime.min, but formatted
        "latest_version": __version__
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
        "message_loading_replays",
        "message_starting_investigation",
        "message_finished_investigation",
        "message_steal_found",
        "message_steal_found_display",
        "message_relax_found",
        "message_relax_found_display",
        "message_correction_found",
        "message_correction_found_display",
        "message_correction_snaps",
        "string_result_steal",
        "string_result_relax",
        "string_result_correction",
        "template_steal",
        "template_relax",
        "template_correction",
        "steal_max_sim",
        "steal_max_sim_display",
        "relax_max_ur",
        "relax_max_ur_display",
        "correction_max_angle",
        "correction_max_angle_display",
        "correction_min_distance",
        "correction_min_distance_display",
        "visualizer_black_bg",
        "required_style",
        "cache_location",
        "log_dir"
    ]
}

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

def overwrite_outdated_settings():
    last_version = version.parse(get_setting("last_version"))
    last_version = version.parse(last_version.base_version)  # remove dev stuff
    for ver, changed_arr in CHANGED.items():
        if last_version < version.parse(ver):
            for setting in changed_arr:
                if setting not in TYPES:
                    # happens if the key is in CHANGED but was deleted in a later version,
                    # like message_cheater_found.
                    continue
                set_setting(setting, DEFAULTS[TYPES[setting][1]][setting])
    set_setting("last_version", __version__)

def overwrite_with_config_settings():
    config = ConfigParser(interpolation=None)
    config.read(CFG_PATH)
    for section in config.sections():
        for k in config[section]:
            try:
                type_ = TYPES[k][0]
            except KeyError:
                # there's a key in the .cfg file that we don't have; ignore it
                continue
            if type_ is bool:
                val = config.getboolean(section, k)
            elif type_ is int:
                val = config.getint(section, k)
            else:
                val = config.get(section, k)
            set_setting(k, val)


def reset_defaults():
    SETTINGS.clear()
    for d in DEFAULTS.values():
        for key,value in d.items():
            SETTINGS.setValue(key, value)
    SETTINGS.sync()


def set_setting(name, value):
    for linkable_setting in LinkableSetting.registered_classes:
        if linkable_setting.filter(name):
            linkable_setting.on_setting_changed(value)

    SETTINGS.setValue(name, TYPES[name][0](value))

# overwrites circleguard.cfg with our settings
def overwrite_config():
    # add file comments at top of file
    with open(CFG_PATH, "w+") as f:
        f.write("### " + COMMENTS["file"].replace("\n", "\n### ") + "\n\n")

    config = ConfigParser(allow_no_value=True, interpolation=None)
    config.optionxform = str # preserve case in setting keys
    for section in DEFAULTS.keys():
        config[section] = {}

    keys = SETTINGS.allKeys()
    # QSettings#allKeys returns a list of keys sorted alphabetically. We want
    # to sort per section by an entry's order in the DEFAULTS dict.
    keys = sorted(keys, key=_index_by_defaults_dict)
    for setting in keys:
        if setting not in TYPES:
            continue
        section = TYPES[setting][1]
        # write section comment before any others
        if config[section] == {} and section in COMMENTS and "section" in COMMENTS[section]:
            comment = "## " + COMMENTS[section]["section"].replace("\n", "\n## ")
            config[section][comment] = None
        if section in COMMENTS and setting in COMMENTS[section]:
            comment = "# " + COMMENTS[section][setting].replace("\n", "\n# ") # comment out each newline
            config[section][comment] = None # setting a configparser key to None writes it as is, without a trailing = for the val

        config[section][setting] = str(SETTINGS.value(setting))

    with open(CFG_PATH, "a+") as f:
        config.write(f)

def _index_by_defaults_dict(key):
    """
    Returns the index of the key in its respective section in the DEFAULTS dict.
    Used to sort a QSettings#allKeys call by each key's position in DEFAULTS.

    Examples
    --------
    DEFAULTS = {
        "category1": {
            "item1": 0
            "item2": 1
        }
    }

    item1 would have an index in category1 of 0, and item2 would have an index
    of 1, so item1 gets sorted above item2 (ie _index_bu_defaults_dict(item1))
    returns 0 and _index_bu_defaults_dict(item2) returns 1.

    Notes
    -----
    Index relative to keys in other sections is not defined. Neither is the
    index if a key in the list does not appear in TYPES (ie, we don't have
    an entry for it in DEFAULTS). This is fine for our purposes, since this is
    only used in overwrite_config and the latter values get thrown out, and for
    the former we segregate keys by setting so only position relative to other
    keys in the section matters.
    """
    if key not in TYPES:
        return 0
    section = TYPES[key][1]
    keys = DEFAULTS[section].keys()
    # https://stackoverflow.com/a/14539017/12164878 for the list cast
    index = list(keys).index(key)
    return index

def initialize_dirs():
    d_dirs = DEFAULTS["Locations"].keys()
    for d_dir in d_dirs:
        parent_path = Path(get_setting(d_dir)).parent
        if not os.path.exists(parent_path):
            os.mkdir(parent_path)

# assemble dict of {key: [type, section], ...} since we have nested dicts in DEFAULTS
# double list comprehension feels sooo backwards to write
# eg {"cache_location": [<class "str">, "Locations"], ...}
TYPES = {k:[type(v), section] for section,d in DEFAULTS.items() for k,v in d.items()}
SETTINGS = QSettings("Circleguard", "Circleguard")
# see third bullet here https://doc.qt.io/qt-5/qsettings.html#platform-limitations,
# we don't want the global keys on macos when calling allkeys
SETTINGS.setFallbacksEnabled(False)

# add setting if missing (occurs between updates if we add a new default setting)
for d in DEFAULTS.values():
    for key,value in d.items():
        if not SETTINGS.contains(key):
            SETTINGS.setValue(key, value)

# create folders if they don't exist
initialize_dirs()


CFG_PATH = get_setting("config_location")

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
