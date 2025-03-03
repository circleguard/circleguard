from PyQt6.QtWidgets import QGridLayout
from PyQt6.QtCore import Qt
from widgets.loadable_base import LoadableBase


class UnselectedLoadable(LoadableBase):
    def __init__(self, parent):
        super().__init__(parent, [])

        self.combobox.setCurrentIndex(0)
        self.disable_button.hide()

        layout = QGridLayout()
        # AlignTop matches the height of the other loadables, as they have more
        # things to display below
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        layout.addWidget(self.combobox, 0, 0, 1, 7)
        layout.addWidget(self.delete_button, 0, 7, 1, 1)
        self.setLayout(layout)

    def disable(self):
        pass

    def check_and_mark_required_fields(self):
        return True

    def cg_loadable(self, previous):
        return None

    def hide_sim_combobox(self):
        pass

    def show_sim_combobox(self):
        pass
