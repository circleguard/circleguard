# pylint: disable=no-name-in-module
from PyQt5.QtCore import QSettings
# pylint: enable=no-name-in-module


def reset_defaults():
    SETTINGS.clear()
    SETTINGS.setValue("ran", True)
    SETTINGS.setValue("threshold", 18)
    SETTINGS.setValue("api_key", "")
    SETTINGS.setValue("dark_theme", 0)
    SETTINGS.setValue("caching", 0)
    SETTINGS.setValue("cache_dir", "./db/")
    SETTINGS.setValue("log_save", 0)
    SETTINGS.setValue("log_dir", "./logs/")
    SETTINGS.setValue("log_mode", 3)
    SETTINGS.setValue("log_output", 0)
    SETTINGS.sync()


SETTINGS = QSettings("Circleguard", "Circleguard")
if not SETTINGS.contains("ran"):
    reset_defaults()

THRESHOLD = SETTINGS.value("threshold")
API_KEY = SETTINGS.value("api_key")
DARK_THEME = SETTINGS.value("dark_theme")
CACHING = SETTINGS.value("caching")
CACHE_DIR = SETTINGS.value("cache_dir")
LOG_SAVE = SETTINGS.value("log_save")
LOG_DIR = SETTINGS.value("log_dir")
LOG_MODE = SETTINGS.value("log_mode")
LOG_OUTPUT = SETTINGS.value("log_output")


def update_default(name, value):
    SETTINGS.setValue(name, value)
