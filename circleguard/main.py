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

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QSettings
import portalocker
from portalocker.exceptions import LockException

from gui.circleguard_window import CircleguardWindow
from settings import get_setting, set_setting
from wizard import CircleguardWizard


# semi randomly chosen
SOCKET_PORT = 4183
LOCK_FILE = Path(tempfile.gettempdir()) / "circleguard_lock.lck"

## set up url handling for windows, which implements custom url schemes by
# launching another instance of the application with the url as an arg. This is
# insanity. We handle the macOS (sane) implementation with
# ``URLHandlingApplication``.

# we can only register url handling for windows at runtime, for macOS we register
# in our plist file, which is set in ``gui_mac.spec``.
if sys.platform == "win32":
    # https://support.shotgunsoftware.com/hc/en-us/articles/219031308-Launching-applications-using-custom-browser-protocols
    hkey_settings = QSettings("HKEY_CLASSES_ROOT\\circleguard", QSettings.NativeFormat)
    hkey_settings.setValue(".", "URL:circleguard Protocol")
    hkey_settings.setValue("URL Protocol", "")
    hkey_open_settings = QSettings("HKEY_CLASSES_ROOT\\circleguard\\shell\\open\\command", QSettings.NativeFormat)
    hkey_open_settings.setValue(".", __file__)

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
# (http://bugs.python.org/issue1230540). This is a hacky workaround that overrides
# the threading init method to use our excepthook.
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


# class URLHandlingApplication(QApplication):
#     url_scheme_called = pyqtSignal(str) # url

#     def __init__(self):
#         super().__init__([])

#     def event(self, event):
#         with open("/Users/tybug/Desktop/a.txt", "w+") as f:
#             f.write(str(event.type() == QEvent.FileOpen))
#             f.write(str(event.type()) + "\n")
#             f.write(str(QEvent.FileOpen))
#             if event.type() == QEvent.FileOpen:
#                 f.write(str(event.url))
#                 self.url_scheme_called.emit(str(event.url))
#         return super().event(event)

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
        except ConnectionAbortedError:
            # happens when we close the serversocket when we quit, just silence
            # the exception
            return
        # arbitrary "large enough" byte receive size
        data = connection.recv(4096)
        circleguard_gui.url_scheme_called(data)

thread = threading.Thread(target=run_server_socket)
thread.start()

app.exec_()
