from PyQt6.QtWidgets import QGridLayout
from widgets.loadable_base import LoadableBase
from widgets.input import InputWidget


class MapUserLoadable(LoadableBase):
    def __init__(self, parent):
        self.map_id_input = InputWidget("Map id", "", "id")
        self.user_id_input = InputWidget("User id", "", "id")
        self.span_input = InputWidget("Span", "", "normal")
        self.span_input.field.setPlaceholderText("all")
        super().__init__(
            parent, [self.map_id_input, self.user_id_input, self.span_input]
        )

        self.combobox.setCurrentIndex(5)

        layout = QGridLayout()
        layout.addWidget(self.combobox, 0, 0, 1, 4)
        layout.addWidget(self.sim_combobox, 0, 4, 1, 2)
        layout.addWidget(self.disable_button, 0, 6, 1, 1)
        layout.addWidget(self.delete_button, 0, 7, 1, 1)
        layout.addWidget(self.map_id_input, 1, 0, 1, 8)
        layout.addWidget(self.user_id_input, 2, 0, 1, 8)
        layout.addWidget(self.span_input, 3, 0, 1, 8)
        self.setLayout(layout)

    def cg_loadable(self, previous):
        from circleguard import MapUser

        # use placeholder text (eg 1-50) if the user inputted span is empty
        span = self.span_input.value() or self.span_input.field.placeholderText()
        if span == "all":
            span = "1-100"

        if not previous or not isinstance(previous, MapUser):
            previous = MapUser(
                int(self.map_id_input.value()), int(self.user_id_input.value()), span
            )

        new_loadable = MapUser(
            int(self.map_id_input.value()), int(self.user_id_input.value()), span
        )

        ret = previous
        if (
            new_loadable.map_id != previous.map_id
            or new_loadable.user_id != previous.user_id
            or new_loadable.span != previous.span
        ):
            ret = new_loadable

        ret.sim_group = self.sim_group
        return ret
