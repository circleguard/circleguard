# pylint: disable=no-name-in-module
from PyQt5.QtCore import QSettings
# pylint: enable=no-name-in-module



def reset_defaults():
    SETTINGS.setValue("ran", True)
    SETTINGS.setValue("threshold", 18)
    SETTINGS.setValue("api_key", "")
    SETTINGS.setValue("dark_theme", 0)
    SETTINGS.setValue("caching", 0)
    SETTINGS.setValue("cache_dir", "./db/")
    SETTINGS.sync()


SETTINGS = QSettings("Circleguard", "Circleguard")
if not SETTINGS.contains("ran"):
    reset_defaults()

THRESHOLD = SETTINGS.value("threshold")
API_KEY = SETTINGS.value("api_key")
DARK_THEME = SETTINGS.value("dark_theme")
CACHING = SETTINGS.value("caching")
CACHE_DIR = SETTINGS.value("cache_dir")


def update_default(name, value):
    SETTINGS.setValue(name, value)
