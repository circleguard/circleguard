from PyQt6.QtWidgets import QFrame, QComboBox, QGraphicsOpacityEffect
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import Qt, pyqtSignal, QEvent
from utils import resource_path
from widgets.combo_box import ComboBox
from widgets.push_button import PushButton


class LoadableBase(QFrame):
    disable_button_shift_clicked = pyqtSignal()

    def __init__(self, parent, required_input_widgets):
        # if we don't pass along a parent correctly here then the loadables
        # flicker as a separate window in the time between instantation and
        # being added to a layout. We should really be setting parents
        # everywhere, but this is the first time it's come back to bite me.
        super().__init__(parent)
        self.required_input_widgets = required_input_widgets
        self._cg_loadable = None
        self.sim_group = 1

        self.delete_button = PushButton(self)
        self.delete_button.setIcon(QIcon(resource_path("delete.png")))
        self.delete_button.setMaximumWidth(30)

        self.disable_button = PushButton(self)
        self.disable_button.setIcon(QIcon(resource_path("enabled.png")))
        self.disable_button.setMaximumWidth(30)
        self.disable_button.clicked.connect(self.disable_button_clicked)
        # so we can detect a shift+click
        self.disable_button.installEventFilter(self)

        self.enabled = True

        self.combobox = ComboBox()
        self.combobox.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        for entry in [
            "Select a Loadable",
            "Map Replay",
            "Local Replay",
            "Map",
            "User",
            "All User Replays on Map",
        ]:
            self.combobox.addItem(entry, entry)

        self.sim_combobox = ComboBox()
        self.sim_combobox.addItem("Sim Group 1", "Sim Group 1")
        self.sim_combobox.addItem("Sim Group 2", "Sim Group 2")
        self.sim_combobox.activated.connect(self.sim_combobox_activated)

    def eventFilter(self, obj, event):
        if (
            obj == self.disable_button
            and event.type() == QEvent.Type.MouseButtonPress
            and event.modifiers() == Qt.KeyboardModifier.ShiftModifier
        ):
            self.disable_button_shift_clicked.emit()
            return True
        return super().eventFilter(obj, event)

    def disable_button_clicked(self):
        if self.enabled:
            self.disable()
        else:
            self.enable()

    def disable(self):
        self.enabled = False
        self.disable_button.setIcon(QIcon(resource_path("disabled.png")))
        # https://stackoverflow.com/a/59022793/12164878
        effect = QGraphicsOpacityEffect(self)
        effect.setOpacity(0.35)
        self.setGraphicsEffect(effect)

    def enable(self):
        self.enabled = True
        self.disable_button.setIcon(QIcon(resource_path("enabled.png")))
        effect = QGraphicsOpacityEffect(self)
        effect.setOpacity(1)
        self.setGraphicsEffect(effect)

    def check_and_mark_required_fields(self):
        all_filled = True
        for input_widget in self.required_input_widgets:
            # don't count inputs with defaults as empty
            filled = (
                input_widget.value() != "" or input_widget.field.placeholderText() != ""
            )
            if not filled:
                input_widget.show_required()
                all_filled = False
        return all_filled

    def hide_sim_combobox(self):
        self.sim_combobox.hide()
        self.layout().removeWidget(self.combobox)
        self.layout().addWidget(self.combobox, 0, 0, 1, 6)

    def show_sim_combobox(self):
        self.sim_combobox.show()
        self.layout().removeWidget(self.combobox)
        self.layout().addWidget(self.combobox, 0, 0, 1, 4)

    def sim_combobox_activated(self):
        if self.sim_combobox.currentData() == "Sim Group 1":
            self.sim_group = 1
        else:
            self.sim_group = 2
