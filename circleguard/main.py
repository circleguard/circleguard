import sys
import threading
import traceback

from PyQt5.QtWidgets import QApplication
import logging

from gui.circleguard_window import CircleguardWindow
from settings import get_setting, set_setting
from wizard import CircleguardWizard

log = logging.getLogger(__name__)

## dirty hacks below! goal is to make execption handling work with threads
# save old excepthook
sys._excepthook = sys.excepthook

# this allows us to log any and all exceptions thrown to a log file -
# pyqt likes to eat exceptions and quit silently
def my_excepthook(exctype, value, tb):
    # call original excepthook before ours
    log.exception("sys.excepthook error\n"
              "Type: " + str(value) + "\n"
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

app.aboutToQuit.connect(circleguard_gui.cancel_all_runs)
app.aboutToQuit.connect(circleguard_gui.on_application_quit)
app.exec_()
