from PyQt6.QtWidgets import QFrame, QLabel, QHBoxLayout
from PyQt6.QtGui import QIcon
from utils import resource_path
from widgets.push_button import PushButton


class PathWidget(QFrame):
    def __init__(self, path):
        super().__init__()
        self.path = path
        # save the loadable we represent so if we load it externally and access
        # it again, it will still be loaded
        self._cg_loadable = None
        label = QLabel(path.name)

        self.delete_button = PushButton(self)
        self.delete_button.setIcon(QIcon(resource_path("delete.png")))
        self.delete_button.setMaximumWidth(25)
        self.delete_button.setMaximumHeight(25)

        layout = QHBoxLayout()
        layout.addWidget(label)
        layout.addWidget(self.delete_button)
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

    def __eq__(self, other):
        if not isinstance(other, PathWidget):
            return False
        return self.path == other.path

    @property
    def cg_loadable(self):
        if not self._cg_loadable:
            from circleguard import ReplayPath

            self._cg_loadable = ReplayPath(self.path)
        return self._cg_loadable
