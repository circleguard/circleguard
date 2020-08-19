import os
from pathlib import Path
import abc
import json
import logging
from functools import partial

from PyQt5.QtCore import QSettings, QStandardPaths
from packaging import version
# it's tempting to use QSettings builtin ini file support instead of
# configparser, but that doesn't let us write comments, which is rather
# important for users.
from configparser import ConfigParser

from version import __version__


COMMENTS = {
    "file": "Please read the following before editing this file.\n"
            "We do not validate or error check these settings, so if you put an incorrect value or syntax, Circleguard may crash on start.\n"
            "If this occurs, you can either fix the error in this file, or delete this file entirely.\n"
            "This will cause a fresh config to be created when circleguard is run again.\n"
            "In places where it is easy to cause issues by editing the settings, we will warn you about it.\n"
            "Some settings use curly braces `{}`, especially the Messages, Strings, and Templates sections.\n"
            "These denote settings to be filled with python's strformat. We do not currently document what variables are passed to you through strformat for each setting.\n"
            "The `ts` seen in many of the settings is a datetime.datetime object, representing the timestamp at that time.\n"
            "You may of course use any formatting directive in the settings (instead of the default %X) that datetime supports.\n\n"
            "After you change settings, you must press the \"sync\" button on the settings tab for them to take effect.\n\n"
            "This file may be edited without Circleguard being open. Any changes will take effect the next time you open Circleguard.",
    "Messages": {
        "section": "Messages written to the terminal (the text box at the bottom of the Main tab) at various times.",
        "message_loading_info": "Displayed when we load the info for replays. Occurs before loading the replays themselves",
        "message_loading_replays": "Displayed when we begin loading replays",
        "message_ratelimited": "Displayed when the api key gets ratelimited",
        "message_finished_investigation": "Displayed when we have finished investigating all replays",
        "message_steal_found": "Displayed when an investigation for replay stealing has a similarity below Thresholds/steal_max_sim",
        "message_steal_found_display": "Displayed when an investigation for replay stealing has a similarity below Thresholds/steal_max_sim_display",
        "message_relax_found": "Displayed when an investigation for relax has a ur below Thresholds/relax_max_ur",
        "message_relax_found_display": "Displayed when an investigation for relax has a ur below Thresholds/relax_max_ur_display",
        "message_correction_found": "Displayed when an investigation for aim correction satisfies both Thresholds/correction_max_angle and correction_min_distance",
        "message_correction_found_display": "Displayed when an investigation for aim correction satisfies both Thresholds/correction_max_angle_display and correction_min_distance_display",
        "message_correction_snaps": "How to represent a snap for aim correction. The result is passed to message_correction_found and message_correction_found_display as `snaps`"
    },
    "Templates": {
        "section": "The templates that are copied to your clipboard from the Results tab \"copy template\" button.",
        "template_steal": "Available for copying for replay stealing results",
        "template_relax": "Available for copying for relax results",
        "template_correction": "Available for copying for aim correction results"
    },
    "Strings": {
        "section": "Labels seen on various widgets.",
        "string_result_steal": "Displayed on the Results tab for a replay stealing result",
        "string_result_relax": "Displayed on the Results tab for a relax result",
        "string_result_correction": "Displayed on the Results tab for an aim correction result"
    },
    "Visualizer": {
        "section": "Settings regarding the replay visualizer.",
        "visualizer_info": "If True, displays some info about the replays while the visualizer is playing",
        "visualizer_black_bg": "If True, uses a pure black background for the visualizer. Otherwise uses the background of the current theme",
        "visualizer_frametime": "If True, displays a frametime graph at the bottom right",
        "default_speed": "The speed the visualizer defaults to when visualizing a new replay",
        "speed_options": "The speed options available to change to in the visualizer. The value of Visualizer/default_speed must appear in this list"
    },
    "Locations": {
        "section": "The paths to various file or directories used by Circleguard.",
        "cache_dir": "Where we store caches for circlecore (replays) and slider (beatmaps).\n"
                "If this location doesn't exist, it will be created, including any nonexistent directories in the path",
        "config_location": "Where the circelguard.cfg file (this very file) resides",
        "log_dir": "Where to write logs. We currently use a single log file (circleguard.log), but the setting is a directory to allow for future expansion"
    },
    "Loadables": {
        "default_span_map": "The default span to use for a Map loadable",
        "default_span_user": "The default span to use for a User loadable"
    },
    "Thresholds": {
        "section": "Thresholds for when to store results and when to display results for various types of cheats.\n"
                "Although possible to set _display settings lower than their respective _cheat setting, it is not advised.",
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
        "section": "How Circleguard looks.",
        "required_style": "The css to apply to a widget if it is required to be filled in to complete an action. This is applied if a required field in a Loadable is empty when you click run, for instance"
    },
    "Logs": {
        "log_save": "Whether to save logs to a file (whose path is defined by Locations/log_dir)",
        "log_level": "All logs with a severity level at or higher than this value will be outputted.\n"
                "Critical: 50\n"
                "Error: 40\n"
                "Warning: 30\n"
                "Info: 20\n"
                "Debug: 10\n"
                "Trace: 5",
        "_log_output": "Where to output logs. This setting has no relation to log_save, so if _log_output is \"none\" and log_save is True, logs will still be written to the log file at the level defined by log_level",
        "log_format": "What format to use for logging"
    },
    "Caching": {
        "caching": "Whether to cache downloaded replays to a file (whose path is defined by Locations/cache_dir)"
    },
    "Tutorial": {
        "section": "Whether you have seen certain tutorial messages or not. These only play once."
    },
    "Misc": {
        "section": "Settings that don't fit in neatly to other sections.",
        "show_cv_frametimes_in_histogram": "If True, displays cv frametimes in the frametime histogram. Otherwise, displays ucv frametimes."
    },
    "Experimental": {
        "section": "These settings are liable to be resource-intensive, behave in unexpected ways, or haven't been tested fully yet. Proceed at your own risk.",
        "rainbow_accent": "Makes the accent color (defines the color of the highlight around the currently focused widget, among other things) constantly cycle through colors"
    },
    "Core": {
        "section": "Internal settings. Don't modify unless you've been told to, or know exactly what you're doing.",
        "ran": "Whether Circleguard has been run on this system before. If False when Circleguard is launched, all settings will be reset to their default and the wizard will be displayed",
        "last_version": "The most recent version of Circleguard run on this system. Used to overwrite settings when they change between versions",
        "api_key": "The api key to use in circlecore",
        "timestamp_format": "The format of last_update_check",
        "last_update_check": "The last time we checked for a new version. Only checks once every hour",
        "latest_version": "The latest Circleguard version available on github"
    }
}




DEFAULTS = {
    "Messages": {
        "message_loading_info":            "[{ts:%X}] Loading replay info",
        "message_loading_replays":         "[{ts:%X}] Loading {num_unloaded} of {num_total} replays ({num_previously_loaded} replays previously loaded)",
        "message_ratelimited":             "[{ts:%X}] Ratelimited, waiting for {s} seconds",
        "message_starting_analysis":       "[{ts:%X}] Preparing replays for analysis, you can visualize (and more) from the Results tab when finished",
        "message_finished_investigation":  "[{ts:%X}] Done",
        "message_no_cheat_found":          "[{ts:%X}] Found nothing below the set thresholds",
        "message_starting_steal":          "[{ts:%X}] Determining similarity of the given replays",
        # it is possible though extremely unusual for the replays to have different map ids. This is good enough
        # replay.mods.short_name is a function, not an attribute, and we can't call functions in format strings. We need to pass mods_short_name and mods_long_name in addition to replay1 and replay2
        "message_steal_found":              "[{ts:%X}] {sim:.1f} similarity. {r.later_replay.username} +{later_replay_mods_short_name} (set later) vs {r.earlier_replay.username} +{earlier_replay_mods_short_name} on map {replay1.map_id}",
        "message_steal_found_display":      "[{ts:%X}] {sim:.1f} similarity. {r.later_replay.username} +{later_replay_mods_short_name} (set later) vs {r.earlier_replay.username} +{earlier_replay_mods_short_name} on map {replay1.map_id}. Not below threshold",
        "message_starting_relax":           "[{ts:%X}] Determining ur of the given replays",
        "message_relax_found":              "[{ts:%X}] {ur:.2f} cvUR. {replay.username} +{mods_short_name} on map {replay.map_id}",
        "message_relax_found_display":      "[{ts:%X}] {ur:.2f} cvUR. {replay.username} +{mods_short_name} on map {replay.map_id}. Not below threshold",
        "message_starting_correction":      "[{ts:%X}] Checking if the given replays contain any Snaps",
        "message_correction_found":         "[{ts:%X}] {replay.username} +{mods_short_name} on map {replay.map_id}. Snaps:\n{snaps}",
        "message_correction_found_display": "[{ts:%X}] {replay.username} +{mods_short_name} on map {replay.map_id}. Snaps:\n{snaps}",
        "message_starting_timewarp":        "[{ts:%X}] Determining frametime of the given replays",
        "message_timewarp_found":           "[{ts:%X}] {frametime:.1f} avg cv frametime. {replay.username} +{mods_short_name} on map {replay.map_id}",
        "message_timewarp_found_display":   "[{ts:%X}] {frametime:.1f} avg cv frametime. {replay.username} +{mods_short_name} on map {replay.map_id}. Not below threshold",
        # have to use a separate message here because we can't loop in ``.format`` strings, can only loop in f strings which only work in a
        # local context and aren't usable for us. Passed as ``snaps=snaps`` in message_correction_found, once formatted. Each snap formats
        # this setting and does a ``"\n".join(snap_message)`` to create ``snaps``.
        "message_correction_snaps":         "Time (ms): {time:.0f}\tAngle (°): {angle:.2f}\tDistance (px): {distance:.2f}"
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
                                "open in circleguard: {circleguard_url}"
                                "\n\n"
                                "{r.similarity:.2f} similarity according to https://github.com/circleguard/circleguard (higher is less similar)"),
        "template_relax":      ("[osu!std] {r.replay.username} | Relax"
                                "\n\n"
                                "Profile: https://osu.ppy.sh/users/{r.replay.user_id}"
                                "\n\n"
                                "Map: https://osu.ppy.sh/b/{r.replay.map_id}"
                                "\n\n"
                                "replay download: https://osu.ppy.sh/scores/osu/{r.replay.replay_id}/download"
                                "\n\n"
                                "open in circleguard: {circleguard_url}"
                                "\n\n"
                                "cvUR: {r.ur:.2f} according to https://github.com/circleguard/circleguard"),
        "template_correction": ("[osu!std] {r.replay.username} | Aim Correction"
                                "\n\n"
                                "Profile: https://osu.ppy.sh/users/{r.replay.user_id}"
                                "\n\n"
                                "Map: https://osu.ppy.sh/b/{r.replay.map_id}"
                                "\n\n"
                                "replay download: https://osu.ppy.sh/scores/osu/{r.replay.replay_id}/download"
                                "\n\n"
                                "open in circleguard: {circleguard_url}"
                                "\n\n"
                                "Snaps according to https://github.com/circleguard/circleguard:"
                                "\n\n"
                                "{snap_table}"),
        "template_timewarp":   ("[osu!std] {r.replay.username} | Timewarp"
                                "\n\n"
                                "Profile: https://osu.ppy.sh/users/{r.replay.user_id}"
                                "\n\n"
                                "Map: https://osu.ppy.sh/b/{r.replay.map_id}"
                                "\n\n"
                                "replay download: https://osu.ppy.sh/scores/osu/{r.replay.replay_id}/download"
                                "\n\n"
                                "open in circleguard: {circleguard_url}"
                                "\n\n"
                                "{frametime:.1f} cv average frametime according to https://github.com/circleguard/circleguard")
    },
    "Strings": {
        "string_result_steal":         "[{ts:%x %H:%M}] {similarity:.1f} similarity. {r.later_replay.username} +{later_replay_mods_short_name} (set later) vs {r.earlier_replay.username} +{earlier_replay_mods_short_name} on map {r1.map_id}",
        "string_result_relax":         "[{ts:%x %H:%M}] {ur:.2f} ur. {replay.username} +{mods_short_name} on map {replay.map_id}",
        "string_result_correction":    "[{ts:%x %H:%M}] {num_snaps} snaps. {replay.username} +{mods_short_name} on map {replay.map_id}",
        "string_result_timewarp":      "[{ts:%x %H:%M}] {frametime:.1f} avg frametime. {replay.username} +{mods_short_name} on map {replay.map_id}",
        "string_result_visualization": "[{ts:%x %H:%M}] {replay_amount} Replays on map {map_id}",
        "string_result_visualization_single": "[{ts:%x %H:%M}] {replay.username} +{mods_short_name} on map {replay.map_id}"
    },
    "Visualizer": {
        "visualizer_info": True,
        "visualizer_black_bg": False,
        "visualizer_frametime": False,
        "render_beatmap": True,
        # so type() returns float, since we want to allow float values, not just int
        "default_speed": float(1),
        "speed_options": [0.1, 0.25, 0.5, 0.75, 1.0, 1.5, 3.0, 5.0, 10.0]
    },
    "Locations": {
        "cache_dir": QStandardPaths.writableLocation(QStandardPaths.AppDataLocation) + "/cache/",
        "log_dir": QStandardPaths.writableLocation(QStandardPaths.AppDataLocation) + "/logs/",
        "config_location": QStandardPaths.writableLocation(QStandardPaths.AppDataLocation)
    },
    "Loadables": {
        "default_span_map": "1-50",
        "default_span_user": ""
    },
    "Thresholds": {
        "steal_max_sim": 17,
        "steal_max_sim_display": 18,
        "relax_max_ur": 50,
        "relax_max_ur_display": 90,
        "correction_max_angle": 10,
        "correction_max_angle_display": 10,
        "correction_min_distance": 8,
        "correction_min_distance_display": 8,
        "timewarp_max_frametime": 13,
        "timewarp_max_frametime_display": 13
    },
    "Appearance": {
        "theme": "dark",
        "theme_options": {
            "Dark": "dark",
            "Light": "light"
        },
        "required_style": "QLineEdit { border: 1px solid red; border-radius: 4px; padding: 2px }\n"
                          "WidgetCombiner { border: 1px solid red; border-radius: 4px; padding: 2px }"
    },
    "Logs": {
        "log_save": True,
        "log_level": 30, # WARNING
        "log_level_options": {
            "TRACE": 5,
            "DEBUG": 10,
            "INFO": 20,
            "WARNING": 30,
            "ERROR": 40,
            "CRITICAL": 50
        },
        # we previously had a setting ``log_output`` which stored a string
        # value. Unfortunately we cannot reuse that setting because if someone
        # upgrades, writes a dict to ``log_output``, then downgrades, we will
        # try to convert a dict to a string and crash. The best workaround for
        # this is to simply avoid changing setting types by using a different
        # name.
        "_log_output": "terminal",
        "_log_output_options": {
            "NONE": "none",
            "TERMINAL": "terminal",
            "NEW WINDOW": "new_window",
            "BOTH": "both"
        },
        "log_format": "[%(levelname)s] %(asctime)s.%(msecs)04d %(message)s (%(name)s, %(filename)s:%(lineno)d)"
    },
    "Caching": {
        "caching": True
    },
    "Tutorial": {
        "tutorial_drag_loadables_seen": False
    },
    "Misc": {
        "frametime_graph_display": "cv",
        "frametime_graph_display_options": {
            "ucv": "ucv",
            "cv": "cv"
        }
    },
    "Experimental": {
        "rainbow_accent": False
    },
    "Core": {
        "ran": False,
        # force run update_settings if the user previously had a version without this key
        "last_version": "0.0.0",
        "api_key": "",
        "timestamp_format": "%Y/%m/%d %H:%M:%S",
        # aka datetime.min, but formatted
        "last_update_check": "1970/01/01 00:00:00",
        "latest_version": __version__
    }
}

FORCE_UPDATE = {
    "1.1.0": [
        "message_cheater_found",
        "message_no_cheater_found",
        "string_result_text"
    ],
    "1.2.0": [
        "message_loading_replays"
    ],
    "2.0.0": [
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
        "visualizer_frametime",
        "render_beatmap",
        "required_style",
        "cache_location",
        "log_dir",
        "cache_dir",
        "timestamp_format",
        "last_update_check"
    ],
    "2.1.1": [
        "speed_options"
    ],
    "2.4.0": [
        "message_relax_found",
        "message_relax_found_display",
        "template_relax"
    ],
    "2.5.0": [
        "log_level"
    ],
    "2.6.0": [
        "timewarp_max_frametime",
        "timewarp_max_frametime_display"
        "message_timewarp_found",
        "message_timewarp_found_display",
        "string_result_timewarp",
        "template_timewarp"
    ],
    "2.6.2": [
        "template_timewarp",
        "message_steal_found",
        "message_steal_found_display",
        "string_result_steal"
    ],
    "2.7.0": [
        "message_starting_investigation_analysis"
    ],
    "2.8.0": [
        "tutorial_drag_loadables_seen",
        "template_timewarp",
        "message_timewarp_found",
        "message_timewarp_found_display"
    ],
    "2.8.1": [
        "log_level",
        "show_cv_frametimes_in_histogram",
        "string_result_visualization_single"
    ],
    "2.9.0": [
        "message_relax_found",
        "message_relax_found_display",
        "string_result_relax",
        "template_steal",
        "template_relax",
        "template_correction",
        "template_timewarp"
    ],
    "2.9.1": [
        "template_steal",
        "template_relax",
        "template_correction",
        "template_timewarp"
    ],
    "2.11.0": [
        "message_starting_analysis"
    ]
}



class LinkableSetting():
    """
    Subclass this to indicate you would like to receive a method call
    (``on_setting_changed``) whenever one of the settings you subscribe to
    changes.

    Warnings
    --------
    Implementation warning for subclases - all python classes must come before
    c classes (like QWidget) or super calls will break. Further reading:
    https://www.riverbankcomputing.com/pipermail/pyqt/2017-January/038650.html

    eg, def MyClass(LinkableSetting, QFrame)
    NOT def MyClass(QFrame, LinkableSetting)
    """
    registered_classes = []
    def __init__(self, settings):
        self.settings = settings
        self.registered_classes.append(self)
        self.setting_values = {}
        for setting in settings:
            val = get_setting(setting)
            self.setting_values[setting] = val

    @abc.abstractmethod
    def on_setting_changed(self, setting, new_value):
        """
        Called when the internal setting this class is linked to is changed,
        from a source other than this class. An extremely common use case - and
        the intended one - is to change the value of a slider/label/other widget
        to reflect the new setting value, so all settings are in sync (gui and
        internal).
        """
        pass

    def filter(self, changed_setting):
        """
        A predicate that returns true if this class should accept signals when
        the given setting is changed (signals in the form of a call to
        on_setting_changed)
        """
        return changed_setting in self.settings

    def on_setting_changed_from_gui(self, setting, value):
        """
        Called when our setting is changed from the gui,
        and our internal settings need to be updated to reflect that.
        """
        if setting not in self.settings:
            raise ValueError(f"expected setting to be one of the subscribed "
                f"settings ({self.settings}). Got {setting} instead.")
        set_setting(setting, value)


class SingleLinkableSetting(LinkableSetting):
    """
    Provided as a conveneince for the common use case of only wanting to
    subscribe to a single setting.
    """
    def __init__(self, setting):
        super().__init__([setting])
        self.setting = setting
        self.setting_value = self.setting_values[setting]

    # TODO maybe also override on_setting_changed to have a signature of
    # def on_setting_changed(self, new_value), since single linkable settings
    # don't care about the name (they already know it!). Would require changing
    # how we dispatch to this method though.

    def on_setting_changed_from_gui(self, value):
        set_setting(self.setting, value)



def get_setting(name):
    type_ = TYPES[name][0]
    val = SETTINGS.value(name)
    # windows registry keys doesnt properly preserve types, so convert "false"
    # keys to a True/False value instead of bool("false") which would return
    # True. See second bullet here:
    # https://doc.qt.io/qt-5/qsettings.html#platform-limitations
    if type_ is bool:
        return False if val in ["false", "False"] else bool(val)
    # val is eg. ['0.10', '1.00', '1.25', '1.50', '2.00'] so convert it to a
    # list of floats, not strings
    if type_ is list:
        val = [float(x) for x in val]
        return val
    if type_ is dict:
        # when dicts get stored in qt's settings I don't think order is
        # preserved, so sort by the order of keys in DEFAULTS.
        sorted_keys = sorted(val.keys(), key=partial(_index_dict_by_default_dict, name))
        # sort by the new keys
        new_val = {}
        for sorted_key in sorted_keys:
            new_val[sorted_key] = val[sorted_key]
        return new_val
    v = type_(val)
    return v

def set_setting(name, value):
    """
    Sets the setting with the given name to have the given value.

    Notes
    -----
    This function also handles any general purpose actions (not relating to gui)
    that need to be taken when settings change, eg setting the log level for all
    loggers when ``log_level`` changes.
    """

    if name == "log_level":
        # set root logger's level
        logging.getLogger().setLevel(value)

    for linkable_setting in LinkableSetting.registered_classes:
        if linkable_setting.filter(name):
            linkable_setting.on_setting_changed(name, value)
    SETTINGS.setValue(name, TYPES[name][0](value))

def toggle_setting(name):
    """
    Toggles the given setting.

    Notes
    -----
    This method is only valid for settings that hold boolean values.
    """
    old_val = get_setting(name)
    new_val = not old_val
    set_setting(name, new_val)

def overwrite_outdated_settings():
    last_version = version.parse(get_setting("last_version"))
    last_version = version.parse(last_version.base_version) # remove dev stuff
    for ver, changed_arr in FORCE_UPDATE.items():
        if last_version < version.parse(ver):
            for setting in changed_arr:
                if setting not in TYPES:
                    # happens if the key is in FORCE_UPDATE but was deleted in a
                    # later version, like message_cheater_found.
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
            elif type_ is float:
                val = config.getfloat(section, k)
            elif type_ is list:
                # config.getlist doesn't exist
                val = json.loads(config.get(section, k))
            elif type_ is dict:
                # config.getdict doesn't exist either, but we also need to
                # convert the single quote representation (which we get when we
                # have  strings in the dict) to double quotes, because
                # `json.loads` wants double quotes
                val = json.loads(config.get(section, k).replace("'", "\""))
            else:
                val = config.get(section, k)
            set_setting(k, val)


def reset_defaults():
    SETTINGS.clear()
    for d in DEFAULTS.values():
        for key,value in d.items():
            set_setting(key, value)
    SETTINGS.sync()


# overwrites circleguard.cfg with our settings
def overwrite_config():
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

        config[section][setting] = str(get_setting(setting))

    with open(CFG_PATH, "w+") as f:
        # add file comments at top of file
        f.write("### " + COMMENTS["file"].replace("\n", "\n### ") + "\n\n")
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
    of 1, so item1 gets sorted above item2 (ie _index_by_defaults_dict(item1))
    returns 0 and _index_by_defaults_dict(item2) returns 1.

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
    # https://stackoverflow.com/a/14539017 for the list cast
    index = list(keys).index(key)
    return index

def _index_dict_by_default_dict(setting_key, key):
    """
    Returns the index of the key in the dict of the setting of ``setting_key``.
    The value of ``setting_key`` must be a dict - that is, TYPES[setting_key][0]
    is a dict.

    Examples
    --------
    If ``setting_key`` is eg ``_log_output``, ``key`` must then be a key in the
    dict which has been assigned to the ``_log_output`` setting, eg ``WARNING``.
    The index of this key in the dict is returned.
    """
    if setting_key not in TYPES:
        return 0
    section = TYPES[setting_key][1]
    keys = DEFAULTS[section][setting_key].keys()
    index = list(keys).index(key)
    return index

def initialize_dirs():
    dirs = DEFAULTS["Locations"].keys()
    for dir_ in dirs:
        path = Path(get_setting(dir_))
        if not path.exists():
            path.mkdir(parents=True)

# assemble dict of {key: [type, section], ...} since we have nested dicts in
# DEFAULTS double list comprehension feels sooo backwards to write
# eg {"cache_dir": [<class "str">, "Locations"], ...}
TYPES = {k:[type(v), section] for section,d in DEFAULTS.items() for k,v in d.items()}
SETTINGS = QSettings("Circleguard", "Circleguard")
# see third bullet here https://doc.qt.io/qt-5/qsettings.html#platform-limitations,
# we don't want the global keys on macos when calling allkeys
SETTINGS.setFallbacksEnabled(False)

# add setting if missing (occurs between updates if we add a new default
# setting)
for d in DEFAULTS.values():
    for key,value in d.items():
        if not SETTINGS.contains(key):
            set_setting(key, value)


CFG_PATH = get_setting("config_location") + "/circleguard.cfg"


# overwrite our settings with the config settings (if the user changed them
# while the application was closed)
overwrite_with_config_settings()

# overwrite setting key if they were changed in a release
# has to be called after overwrite_with_config_settings or the file will
# overwrite our changes here since it's not synced to the file
overwrite_outdated_settings()

# create folders if they don't exist
initialize_dirs()

# create cfg file if it doesn't exist
if not os.path.exists(CFG_PATH):
    overwrite_config()

if not get_setting("ran"):
    reset_defaults()
