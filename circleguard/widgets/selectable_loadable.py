from PyQt6.QtWidgets import QFrame, QVBoxLayout, QStackedLayout
from PyQt6.QtCore import pyqtSignal
from widgets.map_loadable import MapLoadable
from widgets.map_user_loadable import MapUserLoadable
from widgets.replay_map_loadable import ReplayMapLoadable
from widgets.replay_path_loadable import ReplayPathLoadable
from widgets.user_loadable import UserLoadable
from widgets.unselected_loadable import UnselectedLoadable


class SelectableLoadable(QFrame):
    input_changed = pyqtSignal()
    deleted_pressed = pyqtSignal()
    disable_button_shift_clicked = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.previous_mods = None
        self.input_has_changed = False
        # set by LoadableCreation
        self.should_show_sim_combobox = False
        # save the loadable we represent so if we load it externally and access
        # it again, it will still be loaded
        self._cg_loadable = None
        self.type = None

        self.stacked_layout = QStackedLayout()

        unselected = UnselectedLoadable(self)
        unselected.combobox.activated.connect(lambda: self.select_loadable(None))
        unselected.combobox.activated.connect(self._input_changed)
        unselected.delete_button.clicked.connect(self.deleted_pressed)
        unselected.disable_button_shift_clicked.connect(
            self.disable_button_shift_clicked
        )
        self.stacked_layout.addWidget(unselected)

        replay_map = ReplayMapLoadable(self)
        replay_map.combobox.activated.connect(lambda: self.select_loadable(None))
        replay_map.delete_button.clicked.connect(self.deleted_pressed)
        replay_map.disable_button_shift_clicked.connect(
            self.disable_button_shift_clicked
        )
        self.stacked_layout.addWidget(replay_map)

        replay_path = ReplayPathLoadable(self)
        replay_path.combobox.activated.connect(lambda: self.select_loadable(None))
        replay_path.delete_button.clicked.connect(self.deleted_pressed)
        replay_path.disable_button_shift_clicked.connect(
            self.disable_button_shift_clicked
        )
        self.stacked_layout.addWidget(replay_path)

        map_ = MapLoadable(self)
        map_.combobox.activated.connect(lambda: self.select_loadable(None))
        map_.delete_button.clicked.connect(self.deleted_pressed)
        map_.disable_button_shift_clicked.connect(self.disable_button_shift_clicked)
        self.stacked_layout.addWidget(map_)

        user = UserLoadable(self)
        user.combobox.activated.connect(lambda: self.select_loadable(None))
        user.delete_button.clicked.connect(self.deleted_pressed)
        user.disable_button_shift_clicked.connect(self.disable_button_shift_clicked)
        self.stacked_layout.addWidget(user)

        map_user = MapUserLoadable(self)
        map_user.combobox.activated.connect(lambda: self.select_loadable(None))
        map_user.delete_button.clicked.connect(self.deleted_pressed)
        map_user.disable_button_shift_clicked.connect(self.disable_button_shift_clicked)
        self.stacked_layout.addWidget(map_user)

        layout = QVBoxLayout()
        layout.addLayout(self.stacked_layout)
        self.setLayout(layout)

    def select_loadable(self, override_type):
        if (
            not override_type
            and self.stacked_layout.currentWidget().combobox.currentIndex() == 0
        ):
            return

        type_ = (
            override_type or self.stacked_layout.currentWidget().combobox.currentData()
        )
        if type_ == "Map Replay":
            self.stacked_layout.setCurrentIndex(1)
            self.stacked_layout.currentWidget().combobox.setCurrentIndex(1)
        elif type_ == "Local Replay":
            self.stacked_layout.setCurrentIndex(2)
            self.stacked_layout.currentWidget().combobox.setCurrentIndex(2)
        elif type_ == "Map":
            self.stacked_layout.setCurrentIndex(3)
            self.stacked_layout.currentWidget().combobox.setCurrentIndex(3)
        elif type_ == "User":
            self.stacked_layout.setCurrentIndex(4)
            self.stacked_layout.currentWidget().combobox.setCurrentIndex(4)
        elif type_ == "All User Replays on Map":
            self.stacked_layout.setCurrentIndex(5)
            self.stacked_layout.currentWidget().combobox.setCurrentIndex(5)

        if not self.should_show_sim_combobox:
            self.stacked_layout.currentWidget().hide_sim_combobox()
        self.stacked_layout.currentWidget().disable_button.show()

    def _input_changed(self):
        if self.stacked_layout.currentWidget().combobox.currentIndex() == 0:
            return
        self.input_changed.emit()

    @property
    def enabled(self):
        return self.stacked_layout.currentWidget().enabled

    def disable(self):
        self.stacked_layout.currentWidget().disable()

    def enable(self):
        self.stacked_layout.currentWidget().enable()

    def show_delete(self):
        self.stacked_layout.currentWidget().delete_button.show()

    def hide_delete(self):
        self.stacked_layout.currentWidget().delete_button.hide()

    def cg_loadable(self, previous):
        return self.stacked_layout.currentWidget().cg_loadable(previous)

    def check_and_mark_required_fields(self):
        return self.stacked_layout.currentWidget().check_and_mark_required_fields()

    def hide_sim_combobox(self):
        self.stacked_layout.currentWidget().hide_sim_combobox()

    def show_sim_combobox(self):
        self.stacked_layout.currentWidget().show_sim_combobox()
