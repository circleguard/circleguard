"""
This file exists to provide a top-level entry point so local imports will work
in other files.
"""
import sys
import threading
import traceback
import tempfile
from pathlib import Path
import socket
import logging
import configparser
try:
    import winreg
except ImportError:
    # not on windows, ignore
    pass

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
import portalocker
from portalocker.exceptions import LockException

from gui.circleguard_window import CircleguardWindow
from settings import (get_setting, set_setting, initialize_settings,
    initialize_settings_file, CFG_PATH, overwrite_outdated_settings)
from wizard import CircleguardWizard


# semi randomly chosen
SOCKET_PORT = 4183
LOCK_FILE = Path(tempfile.gettempdir()) / "circleguard_lock.lck"

## set up url handling for windows, which implements custom url schemes by
## launching another instance of the application with the url as an arg

# we can only register url handling for windows at runtime, for macOS we register
# in our plist file, which is set in ``gui_mac.spec``.
# this is a build-time-only feature I'm afraid, since we can't call an exe at dev
# time because it hasn't been built yet
if sys.platform == "win32" and hasattr(sys, "_MEIPASS"):
    # we update the location of circleguard.exe every time we run, so if the user
    # ever moves it we'll still correctly redirect the url scheme event to us.
    # I have no idea how other (professional) applications handle this, nor
    # what the proper way to update your url scheme registry is (should it
    # ever be done?).
    try:
        exe_location = str(Path(sys._MEIPASS) / "circleguard.exe") # pylint: disable=no-member
        # most sources I found said to modify HKEY_CLASSES_ROOT, but that requires
        # admin perms. Apparently that registry is just a merger of two other
        # registries, which *don't* require admin perms to write to, so we write
        # there. See https://www.qtcentre.org/threads/7899-QSettings-HKEY_CLASSES_ROOT-access?s=3c32bd8f5e5300b83765040c2d100fe3&p=42379#post42379
        # and https://support.shotgunsoftware.com/hc/en-us/articles/219031308-Launching-applications-using-custom-browser-protocols
        key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, "Software\\Classes\\circleguard")
        # empty string to set (default) value
        winreg.SetValueEx(key, "", 0, winreg.REG_SZ, "URL:circleguard Protocol",)
        winreg.SetValueEx(key, "URL Protocol", 0, winreg.REG_SZ, "")

        key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, "Software\\Classes\\circleguard\\DefaultIcon")
        winreg.SetValueEx(key, "", 0, winreg.REG_SZ, exe_location)

        key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, "Software\\Classes\\circleguard\\shell\\open\\command")
        winreg.SetValueEx(key, "", 0, winreg.REG_SZ, exe_location + " \"%1\"")
    except Exception as e:
        # some users have reported errors ("failure to execute script main")
        # when running circleguard for the first time. This error is a
        # ``PermissionError: [WinError 5] Access denied`` on the following line:
        # ``key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, "Software\\Classes\\circleguard\\DefaultIcon")``.
        # so clearly we don't have permission to create this secondary key for
        # whatever reason, even though the first create key seems to succeed.
        # Oddly enough users who proceed to clone and run circleguard locally
        # report the error disappearing, which I suspect means that windows is
        # giving us different permissions when running through python than when
        # running through pyinstaller / an exe. I don't know enough about
        # windows or registry permissions to make a claim either way.
        # Obviously we would ideally fix this issue at its source, but I don't
        # really have time nor testing grounds to do so at the moment (I cannot
        # reproduce this issue). So we ignore the issue at the cost of users
        # who would have otherwise had circleguard crash for them having
        # circleguard urls not work for them. I think this is an acceptable
        # tradeoff.
        print(f"caught exception {e} while trying to update or create the "
            "circleguard url protocol location.")


# if we're launching this with arguments, it's almost certainly because it
# got called from a circleguard:// url. But if we're not, the user is almost
# certainly launching it manually, after already having one instance open.
# in the latter case we want to launch normally instead of accessing argv,
# which would error.
# Addittionally, we don't want to mess with sockets AT ALL if cg is being
# launched for a second time manually. This ensures that we won't double up
# on sockets by eg creating a duplicate server socket on the same port.
# Unfortunately since we don't lock the file (how could we? it's already
# locked), future instances will have no clue this one exists, and if they are
# called with arguments they will launch themselves instead of redirecting to
# this instance. This is OK for now - if users want to reset to a known state,
# they should close all cg instances and everything will work as expected.
launched_from_url = False
if len(sys.argv) > 1:
    launched_from_url = True

start_server_socket = True


# we lock this file when we start so any circleguard instance knows if another
# instance is running. If so, we pass it our ``argv`` (which came from a url
# scheme) through a socket and then exit.

# ensure it exists
if not LOCK_FILE.exists():
    open(LOCK_FILE, "x").close()
lock_file = open(LOCK_FILE, "r")

try:
    portalocker.lock(lock_file, portalocker.LOCK_EX | portalocker.LOCK_NB)
except LockException:
    if launched_from_url:
        # lock failed, a circleguard application is already running
        clientsocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        clientsocket.connect(("localhost", SOCKET_PORT))
        clientsocket.send(sys.argv[1].encode())
        clientsocket.close()
        sys.exit(0)
    else:
        # if there's already a cg instance running (we know this because our
        # lock to the lock file failed) and we were not launched from a url,
        # this is the second or more instance of cg running. We do not want to
        # start a server socket in this case because then there would be two
        # sockets listening on the same port and it would error.
        start_server_socket = False

if start_server_socket:
    serversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    serversocket.bind(("localhost", SOCKET_PORT))
    serversocket.listen(1)

# use one logger across all of circleguard. So named to avoid conflict with
# circlecore's logger.
log = logging.getLogger("circleguard_gui")

## dirty hacks below! goal is to make execption handling work with threads
# save old excepthook
sys._excepthook = sys.excepthook

# this allows us to log any and all exceptions thrown to a log file -
# pyqt likes to eat exceptions and quit silently
def my_excepthook(exctype, value, tb):
    # call original excepthook before ours
    log.exception("sys.excepthook error\n"
              "Type: " + str(exctype) + "\n"
              "Value: " + str(value) + "\n"
              "Traceback: " + "".join(traceback.format_tb(tb)) + '\n')
    sys._excepthook(exctype, value, tb)

sys.excepthook = my_excepthook

# sys.excepthook doesn't persist across threads
# (http://bugs.python.org/issue1230540). This is a hacky workaround that
# overrides the threading init method to use our excepthook.
# https://stackoverflow.com/a/31622038
threading_init = threading.Thread.__init__
def init(self, *args, **kwargs):
    threading_init(self, *args, **kwargs)
    run_original = self.run

    def run_with_except_hook(*args2, **kwargs2):
        try:
            run_original(*args2, **kwargs2)
        except Exception:
            sys.excepthook(*sys.exc_info())
    self.run = run_with_except_hook
threading.Thread.__init__ = init

# supposedly set by default on qt 6
# QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)

app = QApplication([])
app.setStyle("Fusion")
app.setApplicationName("Circleguard")

initialize_settings()

# TODO find a way to not have to pass app here. We do it to be able to set
# the theme from other widgets
circleguard_gui = CircleguardWindow(app)

# make sure we run after instantiating ``CircleguardWindow`` so that any errors
# show in its console and are visible to the user
try:
    initialize_settings_file()
except configparser.Error:
    log.error("caught error while initializing settings file. This means "
        f"something is wrong with your settings file (located at {CFG_PATH})."
        "You can try deleting that file and restarting circleguard, or you can "
        "ignore this error. It will not affect you unless you want to edit the "
        "advanced settings file, which is something most users do not need to "
        "do.\n\n"
        "Regardless of your choice, please report this on the circleguard "
        "discord; link is in the settings tab. This helps me (tybug) keep "
        "track of how many people are affected by this and what the proper "
        "resolution should be. Thanks!\n\n", exc_info=True)

# overwrite setting key if they were changed in a release
# has to be called after overwrite_with_config_settings or the file will
# overwrite our changes here since it's not synced to the file
overwrite_outdated_settings()

circleguard_gui.show()

if not get_setting("ran"):
    welcome = CircleguardWizard()
    welcome.show()
    set_setting("ran", True)

def close_server_socket():
    serversocket.close()

app.aboutToQuit.connect(circleguard_gui.cancel_all_runs)
app.aboutToQuit.connect(circleguard_gui.on_application_quit)
# if we don't do this it hangs on cmd q
app.aboutToQuit.connect(close_server_socket)

def run_server_socket():
    while True:
        try:
            connection, _ = serversocket.accept()
        except (ConnectionAbortedError, OSError):
            # happens when we close the serversocket when we quit, just silence
            # the exception. Former happens on macos, latter on windows
            return
        # arbitrary "large enough" byte receive size
        data = connection.recv(4096)
        circleguard_gui.url_scheme_called(data)

if start_server_socket:
    thread = threading.Thread(target=run_server_socket)
    thread.start()

# if we're opening for the first time from a url, the lock file won't be
# locked, but we still want to visualize the replay in the url, so fake
# a socket message identical to if the file had been locked
if len(sys.argv) > 1:
    clientsocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    clientsocket.connect(("localhost", SOCKET_PORT))
    clientsocket.send(sys.argv[1].encode())
    clientsocket.close()

def import_expensive_modules():
    # probably not necessary to import every single class - we just want to
    # trigger import-time code by hitting every circleguard file and imports
    # to numpy/scipy therein - but better safe than sorry.
    # pylint: disable=unused-import
    from circleguard import (Circleguard, KeylessCircleguard, LoadableContainer,
        Map, User, MapUser, Replay, ReplayMap, ReplayPath, Mod, Loader,
        Snap, Hit, Span, replay_pairs)
    from circlevis import BeatmapInfo, Visualizer, VisualizerApp
    from slider import Library, Beatmap
    from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT
    from matplotlib.backends.backend_qt5agg import FigureCanvas # pylint: disable=no-name-in-module
    from matplotlib.figure import Figure
    import numpy as np
    # requests isn't that expensive, but might as well load it here anyway
    import requests
    # pylint: enable=unused-import

# everything would work fine if we didn't force import these modules now, but
# the user would experience a potentially multi-second wait time whenever they
# trigger a new import, which would make them think circleguard is broken or
# unresponsive. There's also no downside to force importing them now in a new
# thread (imports are thread safe https://stackoverflow.com/a/12391178/).
thread = threading.Thread(target=import_expensive_modules)
thread.start()

app.exec()
