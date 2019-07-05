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

    # string settings
    SETTINGS.setValue("message_loading_replays", "[{ts:%H}:{ts:%M}:{ts:%S}] Loading {num_replays} Replays")
    SETTINGS.setValue("message_starting_comparing", "[{ts:%H}:{ts:%M}:{ts:%S}] Comparing Replays")
    SETTINGS.setValue("message_finished_comparing", "[{ts:%H}:{ts:%M}:{ts:%S}] Done")
    SETTINGS.setValue("message_cheater_found", "[{ts:%H}:{ts:%M}:{ts:%S}] {similarity} similarity. {replay1_name} vs {replay2_name}, {later_name} set later")

    SETTINGS.sync()


SETTINGS = QSettings("Circleguard", "Circleguard")
if not SETTINGS.contains("ran"):
    reset_defaults()


def get_setting(name):


    return SETTINGS.value(name)


def update_default(name, value):
    SETTINGS.setValue(name, value)
