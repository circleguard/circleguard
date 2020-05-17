from PyQt5.QtWidgets import QApplication

from gui.gui import CircleguardWindow
from settings import get_setting, set_setting
from wizard import CircleguardWizard

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
