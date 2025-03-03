from PyQt6.QtWidgets import QGridLayout
from settings import get_setting
from widgets.loadable_base import LoadableBase
from widgets.input import InputWidget


class UserLoadable(LoadableBase):
    def __init__(self, parent):
        self.user_id_input = InputWidget("User id", "", "id")
        self.span_input = InputWidget("Span", "", "normal")
        self.mods_input = InputWidget("Mods (opt.)", "", "normal")
        self.span_input.field.setPlaceholderText(get_setting("default_span_user"))
        super().__init__(parent, [self.user_id_input, self.span_input])

        self.combobox.setCurrentIndex(4)

        layout = QGridLayout()
        layout.addWidget(self.combobox, 0, 0, 1, 4)
        layout.addWidget(self.sim_combobox, 0, 4, 1, 2)
        layout.addWidget(self.disable_button, 0, 6, 1, 1)
        layout.addWidget(self.delete_button, 0, 7, 1, 1)
        layout.addWidget(self.user_id_input, 1, 0, 1, 8)
        layout.addWidget(self.span_input, 2, 0, 1, 8)
        layout.addWidget(self.mods_input, 3, 0, 1, 8)
        self.setLayout(layout)

    def cg_loadable(self, previous):
        from circleguard import User, Mod, Loader

        # use placeholder text (eg 1-50) if the user inputted span is empty
        span = self.span_input.value() or self.span_input.field.placeholderText()
        if span == "all":
            span = Loader.MAX_USER_SPAN

        if not previous or not isinstance(previous, User):
            mods = (
                Mod(self.mods_input.value().upper())
                if self.mods_input.value()
                else None
            )
            previous = User(int(self.user_id_input.value()), span, mods=mods)

        mods = Mod(self.mods_input.value().upper()) if self.mods_input.value() else None
        new_loadable = User(int(self.user_id_input.value()), span, mods=mods)

        ret = previous
        if (
            new_loadable.user_id != previous.user_id
            or new_loadable.span != previous.span
            or new_loadable.mods != previous.mods
        ):
            ret = new_loadable

        ret.sim_group = self.sim_group
        return ret
