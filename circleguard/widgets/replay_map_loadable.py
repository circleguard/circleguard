from PyQt6.QtWidgets import QGridLayout
from widgets.loadable_base import LoadableBase
from widgets.input import InputWidget


class ReplayMapLoadable(LoadableBase):
    def __init__(self, parent):
        self.previous_mods = None

        self.map_id_input = InputWidget("Map id", "", "id")
        self.user_id_input = InputWidget("User id", "", "id")
        self.mods_input = InputWidget("Mods (opt.)", "", "normal")
        super().__init__(parent, [self.map_id_input, self.user_id_input])

        self.combobox.setCurrentIndex(1)

        layout = QGridLayout()
        layout.addWidget(self.combobox, 0, 0, 1, 4)
        layout.addWidget(self.sim_combobox, 0, 4, 1, 2)
        layout.addWidget(self.disable_button, 0, 6, 1, 1)
        layout.addWidget(self.delete_button, 0, 7, 1, 1)
        layout.addWidget(self.map_id_input, 1, 0, 1, 8)
        layout.addWidget(self.user_id_input, 2, 0, 1, 8)
        layout.addWidget(self.mods_input, 3, 0, 1, 8)
        self.setLayout(layout)

    def cg_loadable(self, previous):
        from circleguard import ReplayMap, Mod

        if not previous or not isinstance(previous, ReplayMap):
            mods = (
                Mod(self.mods_input.value().upper())
                if self.mods_input.value()
                else None
            )
            previous = ReplayMap(
                int(self.map_id_input.value()),
                int(self.user_id_input.value()),
                mods=mods,
            )

        mods = Mod(self.mods_input.value().upper()) if self.mods_input.value() else None
        new_loadable = ReplayMap(
            int(self.map_id_input.value()), int(self.user_id_input.value()), mods=mods
        )

        ret = previous
        if (
            new_loadable.map_id != previous.map_id
            or new_loadable.user_id != previous.user_id
            or self.mods_input.value() != self.previous_mods
        ):
            ret = new_loadable

        self.previous_mods = self.mods_input.value()
        ret.sim_group = self.sim_group
        return ret
