# pylint: disable=no-name-in-module
from PyQt5.QtCore import QSettings
# pylint: enable=no-name-in-module


def reset_defaults():
    SETTINGS.clear()
    SETTINGS.setValue("ran", False)
    SETTINGS.setValue("threshold", 18)
    SETTINGS.setValue("api_key", "")
    SETTINGS.setValue("dark_theme", 0)
    SETTINGS.setValue("caching", 0)
    SETTINGS.setValue("cache_dir", ".")
    SETTINGS.setValue("log_save", 0)
    SETTINGS.setValue("log_dir", "./logs/")
    SETTINGS.setValue("log_mode", 3)
    SETTINGS.setValue("log_output", 0)
    SETTINGS.setValue("local_replay_dir", "./examples/replays/")
    SETTINGS.sync()


SETTINGS = QSettings("Circleguard", "Circleguard")
if not SETTINGS.contains("ran"):
    reset_defaults()


def get_setting(name):
    return SETTINGS.value(name)


def update_default(name, value):
    SETTINGS.setValue(name, value)
