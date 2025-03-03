from PyQt6.QtWidgets import QFrame, QGridLayout, QLabel
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import pyqtSignal
from utils import resource_path
from widgets.input import InputWidget
from widgets.push_button import PushButton


class ReplayMapVis(QFrame):
    input_changed = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.previous_mods = None
        self.input_has_changed = False
        # save the loadable we represent so if we load it externally and access
        # it again, it will still be loaded
        self._cg_loadable = None

        self.map_id_input = InputWidget("Map id", "", "id")
        self.user_id_input = InputWidget("User id", "", "id")
        self.mods_input = InputWidget("Mods (opt.)", "", "normal")

        for input_widget in [self.map_id_input, self.user_id_input]:
            input_widget.field.textChanged.connect(self.input_changed)

        title = QLabel("Online Replay")

        self.delete_button = PushButton(self)
        self.delete_button.setIcon(QIcon(resource_path("delete.png")))
        self.delete_button.setMaximumWidth(30)

        layout = QGridLayout()
        layout.addWidget(title, 0, 0, 1, 7)
        layout.addWidget(self.delete_button, 0, 7, 1, 1)
        layout.addWidget(self.map_id_input, 1, 0, 1, 8)
        layout.addWidget(self.user_id_input, 2, 0, 1, 8)
        layout.addWidget(self.mods_input, 3, 0, 1, 8)
        self.setLayout(layout)

    def validate(self):
        return self.map_id_input.value() and self.user_id_input.value()

    def show_delete(self):
        self.delete_button.show()

    def hide_delete(self):
        self.delete_button.hide()

    def cg_loadable(self):
        from circleguard import ReplayMap, Mod

        if not self.validate():
            return None
        if not self._cg_loadable:
            mods = (
                Mod(self.mods_input.value().upper())
                if self.mods_input.value()
                else None
            )
            self._cg_loadable = ReplayMap(
                int(self.map_id_input.value()),
                int(self.user_id_input.value()),
                mods=mods,
            )
        # if something is accessing the loadable we represent, but the value of
        # our input fields have changed (ie the replay we represent has changed)
        # then we want to return that new loadable instead of always using the
        # old one.
        # To explain the comparison against the previous mods used - if the mods
        # specified by the user have changed in any way, we want to update the
        # loadable. This is because it's ambiguous whether an (unloaded) replay
        # with`mods=None` is equal to a (loaded) replay with the same map and
        # user id, but with `mods=HDHR`. Until the first replay is loaded, we
        # don't know what its mods will end up being, so it could be equal or
        # could not be. To be certain, we recreate the loadable if the mods
        # change at all.
        mods = Mod(self.mods_input.value().upper()) if self.mods_input.value() else None
        new_loadable = ReplayMap(
            int(self.map_id_input.value()), int(self.user_id_input.value()), mods=mods
        )
        if (
            new_loadable.map_id != self._cg_loadable.map_id
            or new_loadable.user_id != self._cg_loadable.user_id
            or self.mods_input.value() != self.previous_mods
        ):
            self._cg_loadable = new_loadable
        self.previous_mods = self.mods_input.value()
        return self._cg_loadable
