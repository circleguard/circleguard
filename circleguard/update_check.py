import requests
from datetime import datetime, timedelta
from settings import get_setting, update_default
from packaging import version
from version import __version__

def run_update_check():
    last_check = datetime.strptime(get_setting("last_update_check"),get_setting("timestamp_format"))
    next_check = last_check + timedelta(hours = 1)
    if next_check < datetime.now():
        try:
            # check for new version
            git_request = requests.get("https://api.github.com/repos/circleguard/circleguard/releases/latest").json()
            git_version = version.parse(git_request["name"])
            update_default("update_version", git_version)
            update_default("last_update_check", datetime.now().strftime(get_setting("timestamp_format")))
        except:  # user is propably offline
            pass
    return get_idle_setting_str()

def get_idle_setting_str():
    current_version = version.parse(__version__)
    if current_version <=  version.parse(get_setting("update_version")):
        return "<a href=\'https://circleguard.dev/download'>Update available!</a>"
    else:
        return "Idle"