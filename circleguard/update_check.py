import requests
from datetime import datetime, timedelta
from settings import get_setting, update_default
from packaging import version
from version import __version__

def run_update_check():
    last_check = datetime.strptime(get_setting("last_update_check"),get_setting("timestamp_format"))
    next_check = last_check + timedelta(hours = 1)
    if next_check < datetime.now() and not get_setting("update_available"):
        # check for new version
        try:
            git_request = requests.get("https://api.github.com/repos/circleguard/circleguard/releases/latest").json()
        except:  # user is propably offline
            return "Idle"
        git_version = version.parse(git_request["name"])
        current_version = version.parse(__version__)
        if current_version < git_version:
            # newer version available
            update_default("update_available", True)
        update_default("last_update_check", datetime.now().strftime(get_setting("timestamp_format")))
    if get_setting("update_available"):
        return "<a href=\'https://circleguard.dev/download'>Update available!</a>"
    else:
        return "Idle"
