from PyQt6.QtWidgets import QGridLayout
from widgets.loadable_base import LoadableBase
from widgets.replay_chooser import ReplayChooser


class ReplayPathLoadable(LoadableBase):
    def __init__(self, parent):
        self.path_input = ReplayChooser()
        super().__init__(parent, [self.path_input])

        self.combobox.setCurrentIndex(2)

        layout = QGridLayout()
        layout.addWidget(self.combobox, 0, 0, 1, 4)
        layout.addWidget(self.sim_combobox, 0, 4, 1, 2)
        layout.addWidget(self.disable_button, 0, 6, 1, 1)
        layout.addWidget(self.delete_button, 0, 7, 1, 1)
        layout.addWidget(self.path_input, 1, 0, 1, 8)
        self.setLayout(layout)

    def cg_loadable(self, previous):
        from circleguard import ReplayPath, ReplayDir

        path = self.path_input.path
        if not previous or not isinstance(previous, (ReplayPath, ReplayDir)):
            if self.path_input.path.is_dir():
                previous = ReplayDir(path)
            else:
                previous = ReplayPath(path)

        if self.path_input.path.is_dir():
            new_loadable = ReplayDir(path)
        else:
            new_loadable = ReplayPath(path)

        previous_path = (
            previous.dir_path if isinstance(previous, ReplayDir) else previous.path
        )
        ret = previous
        if previous_path != path:
            ret = new_loadable

        ret.sim_group = self.sim_group
        return ret

    def check_and_mark_required_fields(self):
        all_filled = True
        for input_widget in self.required_input_widgets:
            filled = input_widget.selection_made
            if not filled:
                input_widget.show_required()
                all_filled = False
        return all_filled
