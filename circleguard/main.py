from PyQt5.QtWidgets import QApplication

from widgets import set_event_window
from gui.gui import WindowWrapper
from settings import get_setting, set_setting
from wizard import CircleguardWizard

app = QApplication([])
app.setStyle("Fusion")
app.setApplicationName("Circleguard")

WINDOW = WindowWrapper()
set_event_window(WINDOW)
WINDOW.resize(900, 750)
WINDOW.show()
if not get_setting("ran"):
    welcome = CircleguardWizard()
    welcome.show()
    set_setting("ran", True)

app.aboutToQuit.connect(WINDOW.cancel_all_runs)
app.aboutToQuit.connect(WINDOW.on_application_quit)
app.exec_()
