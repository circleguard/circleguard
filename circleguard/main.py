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
try:
    import winreg
except ImportError:
    # not on windows, ignore
    pass

from PyQt5.QtWidgets import QApplication
import portalocker
from portalocker.exceptions import LockException

from gui.circleguard_window import CircleguardWindow
from settings import get_setting, set_setting
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
    exe_location = str(Path(sys._MEIPASS) / "circleguard.exe") # pylint: disable=no-member
    # most sources I found said to modify HKEY_CLASSES_ROOT, but that requires
    # admin perms. Apparently that registry is just a merger of two other
    # registries, which *don't* require admin persm to write to, so we write
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
    # lock failed, a circleguard application is already running
    clientsocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    clientsocket.connect(("localhost", SOCKET_PORT))
    clientsocket.send(sys.argv[1].encode())
    clientsocket.close()
    sys.exit(0)

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

app = QApplication([])
app.setStyle("Fusion")
app.setApplicationName("Circleguard")
# TODO find a way to not have to pass app here. We do it to be able to set
# the theme from other widgets
circleguard_gui = CircleguardWindow(app)
circleguard_gui.resize(900, 750)
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
    from circleguard import (Circleguard, KeylessCircleguard, Check, Map, User,
        MapUser, Replay, ReplayMap, ReplayPath, Mod, Loader, Result,
        InvestigationResult, ComparisonResult, StealResult, StealResultCorr,
        StealResultSim, RelaxResult, CorrectionResult, TimewarpResult, Snap,
        Hit, Span)
    from circlevis import BeatmapInfo, Visualizer, VisualizerApp
    from slider import Library, Beatmap
    from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT
    from matplotlib.backends.backend_qt5agg import FigureCanvas # pylint: disable=no-name-in-module
    from matplotlib.figure import Figure
    import numpy as np

# everything would work fine if we didn't force import these modules now, but
# the user would experience a potentially multi-second wait time whenever they
# trigger a new import, which would make them think circleguard is broken or
# unresponsive. There's also no downside to force importing them now in a new
# thread (imports are thread safe https://stackoverflow.com/a/12391178/).
thread = threading.Thread(target=import_expensive_modules)
thread.start()

app.exec_()
