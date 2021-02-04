import sys
from pathlib import Path
from functools import partial
import urllib

from PyQt5.QtWidgets import (QWidget, QFrame, QGridLayout, QLabel, QLineEdit,
    QMessageBox, QSpacerItem, QSizePolicy, QSlider, QSpinBox, QFrame,
    QFileDialog, QPushButton, QCheckBox, QComboBox, QVBoxLayout, QHBoxLayout,
    QMainWindow, QTableWidget, QTableWidgetItem, QAbstractItemView,
    QGraphicsOpacityEffect, QStyle, QListWidget, QListWidgetItem,
    QStackedLayout, QApplication, QShortcut)
from PyQt5.QtGui import (QRegExpValidator, QIcon, QPainter, QPen, QCursor,
    QKeySequence)
from PyQt5.QtCore import (QRegExp, Qt, QCoreApplication, pyqtSignal, QEvent,
    QSize, QTimer)
# from circleguard import Circleguard, TimewarpResult, Mod, Key
# import numpy as np

from settings import (get_setting, reset_defaults, LinkableSetting,
    SingleLinkableSetting)
from utils import resource_path, AnalysisResult, ACCENT_COLOR, spacer


# we want most of our clickable widgets to have a pointing hand cursor on hover

class PushButton(QPushButton):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setCursor(QCursor(Qt.PointingHandCursor))

# TODO set pointer cursor on combobox popup list as well, I tried
# https://stackoverflow.com/a/44525625/12164878 but couldn't get it to work
class ComboBox(QComboBox):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setCursor(QCursor(Qt.PointingHandCursor))
        # remove WheelFocus from the combobox's focus policy
        # https://stackoverflow.com/a/19382766/12164878
        self.setFocusPolicy(Qt.StrongFocus)

    def wheelEvent(self, event):
        # we never want wheel events to scroll the combobox
        event.ignore()

class CheckBox(QCheckBox):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setCursor(QCursor(Qt.PointingHandCursor))

# A slider which moves directly to the clicked position when clicked
# Implementation from https://stackoverflow.com/a/29639127/12164878
class Slider(QSlider):
    def mousePressEvent(self, event):
        self.setValue(QStyle.sliderValueFromPosition(self.minimum(),
            self.maximum(), event.x(), self.width()))

    def mouseMoveEvent(self, event):
        self.setValue(QStyle.sliderValueFromPosition(self.minimum(),
            self.maximum(), event.x(), self.width()))

# TODO cmd + z doesn't undo operations here, figure out why
class LineEdit(QLineEdit):
    def __init__(self, parent):
        super().__init__(parent)
        # save current stylesheet for resetting highlighted style. Don't
        # want to reset to an empty string because our stylesheet may cascade
        # down to here in the future instead of being empty
        self.old_stylesheet = self.styleSheet()
        self.highlighted = False

    def focusInEvent(self, event):
        if self.highlighted:
            self.setStyleSheet(self.old_stylesheet)
            self.highlighted = False
        return super().focusInEvent(event)

    def show_required(self):
        self.setStyleSheet(get_setting("required_style"))
        self.highlighted = True


class PasswordEdit(LineEdit):
    """
    A LineEdit that makes the to show/hide the
    password on focus.
    """

    def __init__(self, parent):
        super().__init__(parent)
        self.setEchoMode(QLineEdit.Password)

    def focusInEvent(self, event):
        self.setEchoMode(QLineEdit.Normal)
        return super().focusInEvent(event)

    def focusOutEvent(self, event):
        self.setEchoMode(QLineEdit.Password)
        return super().focusOutEvent(event)


class IDLineEdit(LineEdit):
    """
    A LineEdit that does not allow anything but digits to be entered.

    Notes
    -----
    Specifically, anything not matched by the regex ``\d*`` is not registered.
    """

    def __init__(self, parent):
        super().__init__(parent)
        validator = QRegExpValidator(QRegExp(r"\d*"))
        self.setValidator(validator)


class QHLine(QFrame):
    def __init__(self, shadow=QFrame.Plain):
        super().__init__()
        self.setFrameShape(QFrame.HLine)
        self.setFrameShadow(shadow)


class QVLine(QFrame):
    def __init__(self, shadow=QFrame.Plain):
        super().__init__()
        self.setFrameShape(QFrame.VLine)
        self.setFrameShadow(shadow)


class Separator(QFrame):
    """
    Creates a horizontal line with text in the middle.
    Useful to vertically separate other widgets.
    """

    def __init__(self, title):
        super().__init__()

        label = QLabel(self)
        label.setText(title)
        label.setAlignment(Qt.AlignCenter)

        self.layout = QGridLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.addWidget(QHLine(), 0, 0, 1, 2)
        self.layout.addWidget(label, 0, 2, 1, 1)
        self.layout.addWidget(QHLine(), 0, 3, 1, 2)
        self.setLayout(self.layout)


class InputWidget(QFrame):
    """
    A container class of widgets that represents user input for an id. This class
    holds a Label and either a PasswordEdit, IDLineEdit, or LineEdit, depending
    on the constructor call. The former two inherit from LineEdit.
    """

    def __init__(self, title, tooltip, type_):
        super().__init__()

        label = QLabel(self)
        label.setText(title+":")
        label.setToolTip(tooltip)
        if type_ == "password":
            self.field = PasswordEdit(self)
        if type_ == "id":
            self.field = IDLineEdit(self)
        if type_ == "normal":
            self.field = LineEdit(self)

        self.layout = QGridLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.addWidget(label, 0, 0, 1, 1)
        self.layout.addItem(spacer(), 0, 1, 1, 1)
        self.layout.addWidget(self.field, 0, 2, 1, 3)
        self.setLayout(self.layout)

    def show_required(self):
        """
        Shows a red border around the LineEdit to indicate a field that must be
        filled in. This border is removed when the LineEdit receieves focus again.
        """
        self.field.show_required()

    def value(self):
        """
        Retrieves the string value of the field in this input widget.
        """
        return self.field.text()


class OptionWidget(SingleLinkableSetting, QFrame):
    """
    A container class of widgets that represents an option with a boolean state.
    This class holds a Label and CheckBox.
    """

    def __init__(self, title, tooltip, setting, end=":"):
        """
        String setting: The name of the setting to link this OptionWidget to.
        """
        SingleLinkableSetting.__init__(self, setting)
        QFrame.__init__(self)

        label = QLabel(self)
        label.setText(title + end)
        label.setToolTip(tooltip)
        self.box = CheckBox(self)
        self.box.setChecked(self.setting_value)
        self.box.stateChanged.connect(self.on_setting_changed_from_gui)
        item = CenteredWidget(self.box)
        item.setFixedWidth(120)
        self.layout = QGridLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.addWidget(label, 0, 0, 1, 1)
        self.layout.addWidget(item, 0, 1, 1, 1, Qt.AlignRight)
        self.setLayout(self.layout)

    def on_setting_changed(self, setting, new_value):
        self.box.setChecked(new_value)


class CenteredWidget(QWidget):
    """
    Turns a widget with a fixed size (for example a QCheckBox) into an flexible one which can be affected by the self.layout.
    """

    def __init__(self, widget):
        super().__init__()
        self.layout = QGridLayout()
        self.layout.setAlignment(Qt.AlignCenter)
        self.layout.setContentsMargins(0,0,0,0)
        self.setContentsMargins(0,0,0,0)
        self.layout.addWidget(widget)
        self.setLayout(self.layout)


class ButtonWidget(QFrame):
    """
    A container class of widgets that represents a clickable action with a label.
    This class holds a QLabel and QPushButton.
    """

    def __init__(self, label_title, button_title, tooltip, end=":"):
        super().__init__()

        label = QLabel(self)
        label.setText(label_title + end)
        label.setToolTip(tooltip)
        self.button = PushButton(button_title)
        self.button.setFixedWidth(120)

        self.layout = QGridLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.addWidget(label, 0, 0, 1, 1)
        self.layout.addItem(spacer(), 0, 1, 1, 1)
        self.layout.addWidget(self.button, 0, 2, 1, 1)
        self.setLayout(self.layout)

class ComboboxSetting(LinkableSetting, QFrame):
    def __init__(self, label_text, tooltip, setting):
        setting_options = setting + "_options"
        LinkableSetting.__init__(self, [setting, setting_options])
        QFrame.__init__(self)

        self.setting = setting

        label = QLabel(self)
        label.setText(label_text + ":")
        label.setToolTip(tooltip)

        combobox = ComboBox(self)
        combobox.setInsertPolicy(QComboBox.NoInsert)
        combobox.setMinimumWidth(120)
        setting_options_dict = self.setting_values[setting_options]
        for text, value in setting_options_dict.items():
            combobox.addItem(text, value)

        # select (in the combobx) the current setting value
        current_value = self.setting_values[setting]
        index = list(setting_options_dict.values()).index(current_value)
        combobox.setCurrentIndex(index)

        combobox.currentIndexChanged.connect(self.selection_changed)

        self.combobox = combobox

        layout = QGridLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(label, 0, 0, 1, 1)
        layout.addItem(spacer(), 0, 1, 1, 1)
        layout.addWidget(combobox, 0, 2, 1, 3, Qt.AlignRight)
        self.setLayout(layout)

    def selection_changed(self):
        self.on_setting_changed_from_gui(self.setting, self.combobox.currentData())


class ScrollableLoadablesWidget(QFrame):
    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout()
        self.layout.setAlignment(Qt.AlignTop)
        self.setLayout(self.layout)


class ScrollableChecksWidget(QFrame):
    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout()
        self.layout.setAlignment(Qt.AlignTop)
        self.setLayout(self.layout)

class LabeledCheckbox(QFrame):
    def __init__(self, label):
        super().__init__()
        label = QLabel(label)
        self.checkbox = CheckBox(self)

        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.checkbox)
        layout.addWidget(label)
        self.setCursor(QCursor(Qt.PointingHandCursor))
        self.setLayout(layout)

    def checked(self):
        return self.checkbox.isChecked()

    # toggle checkbox if we're clicked anywhere, so the label can be clicked to
    # toggle as well
    def mousePressEvent(self, event):
        self.checkbox.toggle()

class InvestigationCheckboxes(QFrame):
    def __init__(self):
        super().__init__()

        self.similarity_cb = LabeledCheckbox("Similarity")
        self.ur_cb = LabeledCheckbox("Unstable Rate")
        self.frametime_cb = LabeledCheckbox("Frametime")
        self.snaps_cb = LabeledCheckbox("Snaps")
        self.manual_analysis_cb = LabeledCheckbox("Manual Analysis")

        layout = QHBoxLayout()
        layout.setSpacing(25)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignLeft)
        layout.addWidget(self.similarity_cb)
        layout.addWidget(self.ur_cb)
        layout.addWidget(self.frametime_cb)
        layout.addWidget(self.snaps_cb)
        layout.addWidget(self.manual_analysis_cb)
        self.setLayout(layout)

    def enabled_investigations(self):
        enabled_investigations = []
        if self.similarity_cb.checkbox.isChecked():
            enabled_investigations.append("Similarity")
        if self.ur_cb.checkbox.isChecked():
            enabled_investigations.append("Unstable Rate")
        if self.frametime_cb.checkbox.isChecked():
            enabled_investigations.append("Frametime")
        if self.snaps_cb.checkbox.isChecked():
            enabled_investigations.append("Snaps")
        if self.manual_analysis_cb.checkbox.isChecked():
            enabled_investigations.append("Manual Analysis")
        return enabled_investigations


class LoadableBase(QFrame):

    disable_button_shift_clicked = pyqtSignal()

    def __init__(self, required_input_widgets):
        super().__init__()
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
        self.combobox.setInsertPolicy(QComboBox.NoInsert)
        for entry in ["Select a Loadable", "Map Replay", "Local Replay", "Map",
            "User", "All User Replays on Map"]:
            self.combobox.addItem(entry, entry)

        self.sim_combobox = ComboBox()
        self.sim_combobox.addItem("Sim Group 1", "Sim Group 1")
        self.sim_combobox.addItem("Sim Group 2", "Sim Group 2")
        self.sim_combobox.activated.connect(self.sim_combobox_activated)

    def eventFilter(self, obj, event):
        if (obj == self.disable_button and
            event.type() == QEvent.MouseButtonPress and
            event.modifiers() == Qt.ShiftModifier):
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
            filled = input_widget.value() != "" or input_widget.field.placeholderText() != ""
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


class UnselectedLoadable(LoadableBase):
    def __init__(self):
        super().__init__([])

        self.combobox.setCurrentIndex(0)
        self.disable_button.hide()

        layout = QGridLayout()
        # AlignTop matches the height of the other loadables, as they have more
        # things to display below
        layout.setAlignment(Qt.AlignTop)
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

class ReplayMapLoadable(LoadableBase):
    def __init__(self):
        self.previous_mods = None

        self.map_id_input = InputWidget("Map id", "", "id")
        self.user_id_input = InputWidget("User id", "", "id")
        self.mods_input = InputWidget("Mods (opt.)", "", "normal")
        super().__init__([self.map_id_input, self.user_id_input])

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

        if not previous:
            mods = Mod(self.mods_input.value()) if self.mods_input.value() else None
            previous = ReplayMap(int(self.map_id_input.value()), int(self.user_id_input.value()), mods=mods)

        mods = Mod(self.mods_input.value()) if self.mods_input.value() else None
        new_loadable = ReplayMap(int(self.map_id_input.value()), int(self.user_id_input.value()), mods=mods)

        ret = previous
        if (new_loadable.map_id != previous.map_id or \
            new_loadable.user_id != previous.user_id or \
            self.mods_input.value() != self.previous_mods):
            ret = new_loadable

        self.previous_mods = self.mods_input.value()
        ret.sim_group = self.sim_group
        return ret


class ReplayPathLoadable(LoadableBase):
    def __init__(self):
        self.path_input = ReplayChooser()
        super().__init__([self.path_input])

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
        if not previous:
            if self.path_input.path.is_dir():
                previous = ReplayDir(path)
            else:
                previous = ReplayPath(path)

        if self.path_input.path.is_dir():
            new_loadable = ReplayDir(path)
        else:
            new_loadable = ReplayPath(path)

        previous_path = previous.dir_path if isinstance(previous, ReplayDir) else previous.path
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


class MapLoadable(LoadableBase):
    def __init__(self):
        self.map_id_input = InputWidget("Map id", "", "id")
        self.span_input = InputWidget("Span", "", "normal")
        self.span_input.field.setPlaceholderText(get_setting("default_span_map"))
        self.mods_input = InputWidget("Mods (opt.)", "", "normal")
        super().__init__([self.map_id_input, self.span_input])

        self.combobox.setCurrentIndex(3)

        layout = QGridLayout()
        layout.addWidget(self.combobox, 0, 0, 1, 4)
        layout.addWidget(self.sim_combobox, 0, 4, 1, 2)
        layout.addWidget(self.disable_button, 0, 6, 1, 1)
        layout.addWidget(self.delete_button, 0, 7, 1, 1)
        layout.addWidget(self.map_id_input, 1, 0, 1, 8)
        layout.addWidget(self.span_input, 2, 0, 1, 8)
        layout.addWidget(self.mods_input, 3, 0, 1, 8)
        self.setLayout(layout)

    def cg_loadable(self, previous):
        from circleguard import Map, Mod, Loader

        # use placeholder text (eg 1-50) if the user inputted span is empty
        span = self.span_input.value() or self.span_input.field.placeholderText()
        if span == "all":
            span = Loader.MAX_MAP_SPAN

        if not previous:
            mods = Mod(self.mods_input.value()) if self.mods_input.value() else None
            previous = Map(int(self.map_id_input.value()), span, mods=mods)

        mods = Mod(self.mods_input.value()) if self.mods_input.value() else None
        new_loadable = Map(int(self.map_id_input.value()), span, mods=mods)

        ret = previous
        if (new_loadable.map_id != previous.map_id or \
            new_loadable.span != previous.span or \
            new_loadable.mods != previous.mods):
            ret = new_loadable

        ret.sim_group = self.sim_group
        return ret


class UserLoadable(LoadableBase):
    def __init__(self):
        self.user_id_input = InputWidget("User id", "", "id")
        self.span_input = InputWidget("Span", "", "normal")
        self.mods_input = InputWidget("Mods (opt.)", "", "normal")
        self.span_input.field.setPlaceholderText(get_setting("default_span_user"))
        super().__init__([self.user_id_input, self.span_input])

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

        if not previous:
            mods = Mod(self.mods_input.value()) if self.mods_input.value() else None
            previous = User(int(self.user_id_input.value()), span, mods=mods)

        mods = Mod(self.mods_input.value()) if self.mods_input.value() else None
        new_loadable = User(int(self.user_id_input.value()), span, mods=mods)

        ret = previous
        if (new_loadable.user_id != previous.user_id or \
            new_loadable.span != previous.span or \
            new_loadable.mods != previous.mods):
            ret = new_loadable

        ret.sim_group = self.sim_group
        return ret


class MapUserLoadable(LoadableBase):
    def __init__(self):
        self.map_id_input = InputWidget("Map id", "", "id")
        self.user_id_input = InputWidget("User id", "", "id")
        self.span_input = InputWidget("Span", "", "normal")
        self.span_input.field.setPlaceholderText("all")
        super().__init__([self.map_id_input, self.user_id_input, self.span_input])

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

        if not previous:
            previous = MapUser(int(self.map_id_input.value()), int(self.user_id_input.value()), span)

        new_loadable = MapUser(int(self.map_id_input.value()), int(self.user_id_input.value()), span)

        ret = previous
        if (new_loadable.map_id != previous.map_id or \
            new_loadable.user_id != previous.user_id or \
            new_loadable.span != previous.span):
            ret = new_loadable

        ret.sim_group = self.sim_group
        return ret


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

        unselected = UnselectedLoadable()
        unselected.combobox.activated.connect(lambda: self.select_loadable())
        unselected.combobox.activated.connect(self._input_changed)
        unselected.delete_button.clicked.connect(self.deleted_pressed)
        unselected.disable_button_shift_clicked.connect(self.disable_button_shift_clicked)
        self.stacked_layout.addWidget(unselected)

        replay_map = ReplayMapLoadable()
        replay_map.combobox.activated.connect(lambda: self.select_loadable())
        replay_map.delete_button.clicked.connect(self.deleted_pressed)
        replay_map.disable_button_shift_clicked.connect(self.disable_button_shift_clicked)
        self.stacked_layout.addWidget(replay_map)

        replay_path = ReplayPathLoadable()
        replay_path.combobox.activated.connect(lambda: self.select_loadable())
        replay_path.delete_button.clicked.connect(self.deleted_pressed)
        replay_path.disable_button_shift_clicked.connect(self.disable_button_shift_clicked)
        self.stacked_layout.addWidget(replay_path)

        map_ = MapLoadable()
        map_.combobox.activated.connect(lambda: self.select_loadable())
        map_.delete_button.clicked.connect(self.deleted_pressed)
        map_.disable_button_shift_clicked.connect(self.disable_button_shift_clicked)
        self.stacked_layout.addWidget(map_)

        user = UserLoadable()
        user.combobox.activated.connect(lambda: self.select_loadable())
        user.delete_button.clicked.connect(self.deleted_pressed)
        user.disable_button_shift_clicked.connect(self.disable_button_shift_clicked)
        self.stacked_layout.addWidget(user)

        map_user = MapUserLoadable()
        map_user.combobox.activated.connect(lambda: self.select_loadable())
        map_user.delete_button.clicked.connect(self.deleted_pressed)
        map_user.disable_button_shift_clicked.connect(self.disable_button_shift_clicked)
        self.stacked_layout.addWidget(map_user)

        layout = QVBoxLayout()
        layout.addLayout(self.stacked_layout)
        self.setLayout(layout)

    def select_loadable(self, override_type=None):
        if not override_type and self.stacked_layout.currentWidget().combobox.currentIndex() == 0:
            return

        type_ = override_type or self.stacked_layout.currentWidget().combobox.currentData()
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


class LoadableCreation(QFrame):
    LOADABLE_SIZE = QSize(450, 150)

    def __init__(self):
        super().__init__()
        self.loadables = []
        self.previous_combobox_state = None

        self.list_widget = QListWidget()
        self.list_widget.setResizeMode(QListWidget.Adjust)
        self.list_widget.setViewMode(QListWidget.IconMode)
        self.list_widget.setGridSize(self.LOADABLE_SIZE)
        # apparently list widgets allow you to move widgets around? We don't
        # want to allow that though.
        self.list_widget.setMovement(QListWidget.Static)

        self.cg_loadables_to_selectable_loadables = {}

        QShortcut(QKeySequence(Qt.Key_R), self, lambda: self.select_loadable("Map Replay"))
        QShortcut(QKeySequence(Qt.Key_L), self, lambda: self.select_loadable("Local Replay"))
        QShortcut(QKeySequence(Qt.Key_M), self, lambda: self.select_loadable("Map"))
        QShortcut(QKeySequence(Qt.Key_U), self, lambda: self.select_loadable("User"))
        QShortcut(QKeySequence(Qt.Key_A), self, lambda: self.select_loadable("All User Replays on Map"))

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignTop)
        layout.addWidget(self.list_widget)
        self.setLayout(layout)

        # prepopulate with a single loadable
        self.new_loadable()

    def reset_active_window(self):
        # See the caller of this method for reasoning as to why this method
        # exists.
        # imported locally here to avoid circular imports
        from gui.circleguard_window import CircleguardWindow
        QApplication.setActiveWindow(CircleguardWindow.INSTANCE)

    def loadable_input_changed(self, loadable):
        # only allow the bottommost loadable to create new ones
        if loadable != self.most_recent_loadable:
            return
        self.new_loadable()

    def resizeEvent(self, event):
        ret = super().resizeEvent(event)
        # I don't totally understand how, but the positions of the loadables in
        # the list widget can get into a bad state when the window is resized.
        # A recalculation of the layout seems to fix this, so force recalc on
        # every resize event.
        self.list_widget.scheduleDelayedItemsLayout()
        return ret

    def select_loadable(self, type_):
        self.most_recent_loadable.select_loadable(type_)
        self.new_loadable()

    def new_loadable(self, type_=None):
        loadable = SelectableLoadable()
        self.cg_loadables_to_selectable_loadables[loadable] = None
        loadable.should_show_sim_combobox = self.previous_combobox_state == Qt.Checked
        # some loadables have input widgets which can become arbitrarily long,
        # for instance ReplayPathLoadable's ReplayChooser which displays the
        # chosen file's location. This would cause the loadable to increase in
        # size in the list widget, which looks terrible as the list widget
        # expects uniform size.
        # Long story short enforce constant size on loadables no matter what.
        loadable.setFixedSize(self.LOADABLE_SIZE)

        loadable.deleted_pressed.connect(lambda: self.remove_loadable(loadable))
        loadable.input_changed.connect(lambda: self.loadable_input_changed(loadable))
        loadable.disable_button_shift_clicked.connect(lambda: self.disable_button_shift_clicked(loadable))
        # don't allow the bottommost loadable (which this new one will soon
        # become) to be deleted, users could accidentally remove all loadables
        loadable.hide_delete()

        self.most_recent_loadable = loadable
        self.loadables.append(loadable)
        # show the delete button on the second to last handler, if it exists,
        # since it can now be deleted as it isn't the final loadable
        if len(self.loadables) > 1:
            self.loadables[-2].show_delete()

        # god bless this SO answer https://stackoverflow.com/a/49272941/12164878
        # I would never have thought to set the size hint manually otherwise
        # (and doing so is very much necessary).
        item = QListWidgetItem(self.list_widget)
        self.list_widget.addItem(item)
        item.setSizeHint(self.LOADABLE_SIZE)
        # list items get an annoying highlight in the middle of the widget if
        # we don't disable interaction.
        item.setFlags(item.flags() & ~Qt.ItemIsEnabled)
        self.list_widget.setItemWidget(item, loadable)
        # without this call, list items will be added in the wrong spot
        # and will only correct themselves once the window is resized or another
        # loadable is added. I'm probably doing something wrong that's the
        # root cause of this behavior, but I can't figure out what and this call
        # fixes it.
        # https://stackoverflow.com/a/48773670/12164878
        self.list_widget.scheduleDelayedItemsLayout()

        # This is a weird one. Adding our ``SelectableLoadable`` to the list
        # widget causes our main window (``CircleguardWindow``) to not be the
        # active window anymore, which means any mouse clicks onto widgets that
        # want to receive focus (like LineEdits) will not recieve focus until
        # the window becomes the main window again. So we have to force the
        # CircleguardWindow to be the main window.
        # However, if we do so directly here, the cg window will still not be
        # the main window afterwards. I believe this is because the list widget
        # is scheduling some events to be fired shortly afterwards that is
        # causing the active window removal, so we need to wait for those to
        # occurr before we can do anything. Even 10ms seemed to work, but I'm
        # going for 100 to be safe.
        timer = QTimer(self)
        timer.setSingleShot(True)
        timer.timeout.connect(self.reset_active_window)
        timer.start(100)

    def remove_loadable(self, loadable):
        # since we're dealing with a QListWidget, we can't just hide the
        # loadable widget - we need to remove it from the list widget entirely.
        # In typical qt fashion, the only way to do so is with an index into the
        # list widget.
        index = self.loadables.index(loadable)
        self.loadables.remove(loadable)
        self.list_widget.takeItem(index)
        if loadable == self.most_recent_loadable:
            self.most_recent_loadable = self.loadables[-1]

        # necessary to reclaim this memory when we delete the associated
        # loadable
        self.cg_loadables_to_selectable_loadables[loadable] = None

    def disable_button_shift_clicked(self, caller_loadable):
        # a shift click on a loadable that is enabled means we want to disable
        # every *other* loadable.
        if caller_loadable.enabled:
            for loadable in self.loadables:
                if loadable != caller_loadable:
                    loadable.disable()
        # but a shift click on a disabled loadable means we want to enable *all*
        # loadables.
        else:
            for loadable in self.loadables:
                loadable.enable()


    def cg_loadables(self):
        """
        Returns the loadables in this widget as (potentially) unloaded
        circleguard loadables.
        """
        loadables = []
        for loadable in self.loadables:
            # loadables can be selectively enabled or disabled
            if not loadable.enabled:
                continue
            previous = self.cg_loadables_to_selectable_loadables[loadable]
            cg_loadable = loadable.cg_loadable(previous)
            self.cg_loadables_to_selectable_loadables[loadable] = cg_loadable
            # can't do ``not cg_loadable`` because for ReplayContainers they
            # may not be loaded yet and so have length 0 and are thus falsey,
            # but we still want to return them
            if cg_loadable is None:
                continue
            loadables.append(cg_loadable)
        return loadables

    def check_and_mark_required_fields(self):
        all_valid = True
        for loadable in self.loadables:
            # only check enabled loadables, disabled + empty loadables should
            # not stop the run from succeeding
            if loadable.enabled and not loadable.check_and_mark_required_fields():
                all_valid = False
        return all_valid

    def similarity_cb_state_changed(self, state):
        self.previous_combobox_state = state
        for loadable in self.loadables:
            if state == Qt.Unchecked:
                loadable.hide_sim_combobox()
            else:
                loadable.show_sim_combobox()
            loadable.should_show_sim_combobox = state == Qt.Checked

# provided for our Analysis window. There's probably some shared code that
# we could abstract out from this and `DropArea`, but it's not worth it atm
class ReplayDropArea(QFrame):
    def __init__(self):
        super().__init__()
        self.path_widgets = []

        self.setAcceptDrops(True)

        self.info_label = QLabel("drag and drop .osr files here")
        font = self.info_label.font()
        font.setPointSize(20)
        self.info_label.setFont(font)
        self.info_label.setAlignment(Qt.AlignCenter)

        # https://stackoverflow.com/a/59022793/12164878
        effect = QGraphicsOpacityEffect(self)
        effect.setOpacity(0.5)
        self.info_label.setGraphicsEffect(effect)
        self.info_label.setAutoFillBackground(True)

        layout = QGridLayout()
        layout.setContentsMargins(25, 25, 10, 10)
        layout.addWidget(self.info_label)
        self.setLayout(layout)

    def dragEnterEvent(self, event):
        event.acceptProposedAction()

    def dropEvent(self, event):
        mimedata = event.mimeData()
        # users can drop multiple files, in which case we need to consider each
        # separately
        paths_unprocessed = mimedata.data("text/uri-list").data().decode("utf-8").rstrip().replace("file:///", "").replace("\r", "")
        path_widgets = []

        for path in paths_unprocessed.split("\n"):
            # I might be misunderstanding mime URIs, but it seems to me that
            # files are always prepended with `file:///` on all platforms, but
            # on macOS the leading slash is not included (there are only three
            # slashes, not four), which confuses pathlib as it will interpret
            # the path as relative and not absolute. To fix this we prepend a
            # slash on macOS, but not windows, as their denotation for a root
            # dir is different (they use `C:`).
            if sys.platform == "darwin":
                path = "/" + path
            # if the file path has a space (or I believe any character which
            # requires an encoding), qt will give it to us in its encoded form.
            # Pathlib doesn't like this, so we need to unencode (unquote) it.
            path = urllib.parse.unquote(path)
            path = Path(path)
            if not (path.suffix == ".osr" or path.is_dir()):
                continue

            to_add = []
            if path.is_dir():
                for replay_path in path.glob("*.osr"):
                    path_widget = PathWidget(replay_path)
                    to_add.append(path_widget)
            else:
                path_widget = PathWidget(path)
                to_add.append(path_widget)

            for path_widget in to_add:
                # don't let users drop the same file twice
                if path_widget in self.path_widgets:
                    continue
                path_widgets.append(path_widget)

        # if none of the files were replays, don't accept the drop event
        if not path_widgets:
            return

        event.acceptProposedAction()
        # hide the info label and fill top down now that we have things to show
        self.info_label.hide()
        self.layout().setAlignment(Qt.AlignLeft | Qt.AlignTop)

        for path_widget in path_widgets:
            # `lambda` is late binding so we can't use it here or else all the
            # delete buttons will delete the last widget of the list.
            # workaround: use `partial` instead of `lambda`.
            # https://docs.python-guide.org/writing/gotchas/#late-binding-closures
            path_widget.delete_button.clicked.connect(partial(self.delete_path_widget, path_widget))
            self.layout().addWidget(path_widget)

        self.path_widgets.extend(path_widgets)

    def delete_path_widget(self, path_widget):
        path_widget.hide()
        self.path_widgets.remove(path_widget)

        # re-show the info label if the user deletes all their replays
        if len(self.path_widgets) == 0:
            self.layout().setAlignment(Qt.Alignment())
            self.info_label.show()

    def all_loadables(self):
        return [path_widget.cg_loadable for path_widget in self.path_widgets]

    def paintEvent(self, event):
        super().paintEvent(event)
        pen = QPen()
        pen.setColor(ACCENT_COLOR)
        pen.setWidth(3)
        # 4 (pen width units of) accent color, followed by 4 (pen width units
        # of) nothing, then repeat
        pen.setDashPattern([4, 4])
        painter = QPainter(self)
        painter.setPen(pen)
        painter.drawRoundedRect(0, 5, self.width() - 5, self.height() - 7, 3, 3)


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


class ReplayMapCreation(QFrame):
    def __init__(self):
        super().__init__()
        self.loadables = []

        label = QLabel("Select online replays here")
        font = label.font()
        font.setPointSize(17)
        label.setFont(font)
        effect = QGraphicsOpacityEffect(self)
        effect.setOpacity(0.8)
        label.setGraphicsEffect(effect)
        label.setAutoFillBackground(True)

        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignTop)
        layout.addWidget(label)
        self.setLayout(layout)

        # prepopulate with a single loadable
        self.new_loadable()

    def loadable_input_changed(self, loadable):
        # only allow the bottommost loadable to create new ones
        if loadable != self.most_recent_loadable:
            return
        self.new_loadable()

    def new_loadable(self):
        loadable = ReplayMapVis()
        loadable.delete_button.clicked.connect(lambda: self.remove_loadable(loadable))
        loadable.input_changed.connect(lambda: self.loadable_input_changed(loadable))
        # don't allow the bottommost loadable (which this new one will soon
        # become) to be deleted, users could accidentally remove all loadables
        loadable.hide_delete()

        self.most_recent_loadable = loadable
        self.loadables.append(loadable)
        # show the delete button on the second to last handler, if it exists,
        # since it can now be deleted as it isn't the final loadable
        if len(self.loadables) > 1:
            self.loadables[-2].show_delete()

        self.layout().addWidget(loadable)

    def remove_loadable(self, loadable):
        loadable.hide()
        self.loadables.remove(loadable)
        if loadable == self.most_recent_loadable:
            self.most_recent_loadable = self.loadables[-1]

    def all_loadables(self):
        """
        Returns the loadables in this widget as unloaded circleguard loadables.
        """
        loadables = []
        for loadable in self.loadables:
            cg_loadable = loadable.cg_loadable()
            if not cg_loadable:
                continue
            loadables.append(cg_loadable)
        return loadables




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
            mods = Mod(self.mods_input.value()) if self.mods_input.value() else None
            self._cg_loadable = ReplayMap(int(self.map_id_input.value()), int(self.user_id_input.value()), mods=mods)
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
        mods = Mod(self.mods_input.value()) if self.mods_input.value() else None
        new_loadable = ReplayMap(int(self.map_id_input.value()), int(self.user_id_input.value()), mods=mods)
        if (new_loadable.map_id != self._cg_loadable.map_id or \
            new_loadable.user_id != self._cg_loadable.user_id or \
            self.mods_input.value() != self.previous_mods):
            self._cg_loadable = new_loadable
        self.previous_mods = self.mods_input.value()
        return self._cg_loadable



class ResultW(QFrame):
    """
    Stores the result of a comparison that can be replayed at any time.
    Contains a QLabel, QPushButton (visualize) and QPushButton (copy to clipboard).
    """
    template_button_pressed_signal = pyqtSignal()
    visualize_button_pressed_signal = pyqtSignal()

    def __init__(self, text, result, replays):
        super().__init__()
        self.result = result
        self.replays = replays

        self.label = QLabel(self)
        self.label.setText(text)
        self.label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.label.setCursor(QCursor(Qt.IBeamCursor))

        self.visualize_button = PushButton(self)
        self.visualize_button.setText("Visualize")
        self.visualize_button.clicked.connect(self.visualize_button_pressed_signal.emit)

        if len(replays) == 1:
            self.set_layout_single()
        # at the moment, this only happens for replay stealing and when
        # visualizing multiple replays
        else:
            self.set_layout_multiple()

    def set_layout_single(self):
        self.actions_combobox = ComboBox()
        self.actions_combobox.addItem("More")
        self.actions_combobox.addItem("View Frametimes", "View Frametimes")
        self.actions_combobox.addItem("View Replay Data", "View Replay Data")
        self.actions_combobox.setInsertPolicy(QComboBox.NoInsert)
        self.actions_combobox.activated.connect(self.action_combobox_activated)

        layout = QGridLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.label, 0, 0, 1, 4)
        layout.addItem(spacer(), 0, 4, 1, 1)
        if isinstance(self.result, AnalysisResult):
            layout.addWidget(self.visualize_button, 0, 5, 1, 3)
            layout.addWidget(self.actions_combobox, 0, 8, 1, 1)
        else:
            template_button = self.new_template_button()

            layout.addWidget(self.visualize_button, 0, 5, 1, 2)
            layout.addWidget(template_button, 0, 7, 1, 1)
            layout.addWidget(self.actions_combobox, 0, 8, 1, 1)

        self.setLayout(layout)

    def set_layout_multiple(self):
        layout = QGridLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.label, 0, 0, 1, 1)
        layout.addItem(spacer(), 0, 1, 1, 1)
        if isinstance(self.result, AnalysisResult):
            layout.addWidget(self.visualize_button, 0, 2, 1, 2)
        else:
            template_button = self.new_template_button()
            layout.addWidget(self.visualize_button, 0, 2, 1, 1)
            layout.addWidget(template_button, 0, 3, 1, 1)

        self.setLayout(layout)

    def action_combobox_activated(self):
        if self.actions_combobox.currentData() == "View Frametimes":
            self.frametime_window = FrametimeWindow(self.result, self.replays[0])
            self.frametime_window.show()
        if self.actions_combobox.currentData() == "View Replay Data":
            self.replay_data_window = ReplayDataWindow(self.replays[0])
            self.replay_data_window.show()
        self.actions_combobox.setCurrentIndex(0)

    def new_template_button(self):
        template_button = PushButton(self)
        template_button.setText("Copy Template")
        template_button.setFixedWidth(120)
        template_button.clicked.connect(self.template_button_pressed_signal.emit)
        return template_button

class FrametimeWindow(QMainWindow):
    def __init__(self, result, replay):
        super().__init__()
        # XXX make sure to import matplotlib after pyqt, so it knows to use that
        # and not re-import it.
        from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT

        self.setWindowTitle("Replay Frametime")
        self.setWindowIcon(QIcon(resource_path("logo/logo.ico")))

        frametime_graph = FrametimeGraph(result, replay)
        self.addToolBar(NavigationToolbar2QT(frametime_graph.canvas, self))
        self.setCentralWidget(frametime_graph)
        self.resize(600, 500)


class FrametimeGraph(QFrame):

    def __init__(self, result, replay):
        super().__init__()
        from circleguard import KeylessCircleguard
        from matplotlib.backends.backend_qt5agg import FigureCanvas # pylint: disable=no-name-in-module
        from matplotlib.figure import Figure

        figure = Figure(figsize=(5,5))
        cg = KeylessCircleguard()
        show_cv = get_setting("frametime_graph_display") == "cv"
        figure = cg.frametime_graph(replay, cv=show_cv, figure=figure)

        self.canvas = FigureCanvas(figure)

        layout = QVBoxLayout()
        layout.addWidget(self.canvas)
        self.setLayout(layout)


class ReplayDataWindow(QMainWindow):
    def __init__(self, replay):
        super().__init__()
        self.setWindowTitle("Raw Replay Data")
        self.setWindowIcon(QIcon(resource_path("logo/logo.ico")))

        replay_data_table = ReplayDataTable(replay)
        self.setCentralWidget(replay_data_table)
        self.resize(500, 700)

class ReplayDataTable(QFrame):
    def __init__(self, replay):
        super().__init__()
        from circleguard import Key

        table = QTableWidget()
        table.setColumnCount(4)
        table.setRowCount(len(replay.t))
        table.setHorizontalHeaderLabels(["Time (ms)", "x", "y", "keys pressed"])
        # https://forum.qt.io/topic/82749/how-to-make-qtablewidget-read-only
        table.setEditTriggers(QAbstractItemView.NoEditTriggers)

        for i, data in enumerate(zip(replay.t, replay.xy, replay.k)):
            t, xy, k = data
            if i == 0:
                text = str(t)
            else:
                t_prev = replay.t[i - 1]
                text = f"{t} ({t - t_prev})"

            item = QTableWidgetItem(text)
            table.setItem(i, 0, item)

            item = QTableWidgetItem(str(xy[0]))
            table.setItem(i, 1, item)

            item = QTableWidgetItem(str(xy[1]))
            table.setItem(i, 2, item)

            ks = []
            if Key.K1 & k:
                ks.append("K1")
            # M1 is always set if K1 is set, so only append if it's set without
            # K1. Same with M2/K2
            elif Key.M1 & k:
                ks.append("M1")
            if Key.K2 & k:
                ks.append("K2")
            elif Key.M2 & k:
                ks.append("M2")
            item = QTableWidgetItem(" + ".join(ks))
            table.setItem(i, 3, item)

        layout = QVBoxLayout()
        layout.addWidget(table)
        self.setLayout(layout)


class RunWidget(QFrame):
    """
    A single run with QLabel displaying a state (either queued, finished,
    loading replays, comparing, or canceled), and a cancel QPushButton
    if not already finished or canceled.
    """

    def __init__(self, run):
        super().__init__()

        self.status = "Queued"
        self.label = QLabel(self)
        self.text = f"Run with {len(run.loadables)} Loadables"
        self.label.setText(self.text)

        self.status_label = QLabel(self)
        self.status_label.setText("<b>Status: " + self.status + "</b>")
        self.status_label.setTextFormat(Qt.RichText) # so we can bold it
        self.button = PushButton(self)
        self.button.setText("Cancel")
        self.button.setFixedWidth(50)
        self.label.setFixedHeight(self.button.size().height()*0.75)

        self.layout = QGridLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.addWidget(self.label, 0, 0, 1, 1)
        self.layout.addWidget(self.status_label, 0, 1, 1, 1)
        # needs to be redefined because RunWidget is being called from a
        # different thread or something? get weird errors when not redefined
        SPACER = QSpacerItem(100, 0, QSizePolicy.Maximum, QSizePolicy.Minimum)
        self.layout.addItem(SPACER, 0, 2, 1, 1)
        self.layout.addWidget(self.button, 0, 3, 1, 1)
        self.setLayout(self.layout)

    def update_status(self, status):
        if status in ["Finished", "Invalid arguments"]:
            # not a qt function, pyqt's implementation of deleting a widget
            self.button.deleteLater()

        self.status = status
        self.status_label.setText("<b>Status: " + self.status + "</b>")

    def cancel(self):
        self.status = "Canceled"
        self.button.deleteLater()
        self.status_label.setText("<b>Status: " + self.status + "</b>")



class SliderBoxSetting(SingleLinkableSetting, QFrame):
    """
    A container class of a QLabel, QSlider, and SpinBox, and links the slider
    and spinbox to a setting (ie the default values of the slider and spinbox
    will be the value of the setting, and changes made to the slider or
    spinbox will affect the setting).
    """

    def __init__(self, parent, display, tooltip, setting, max_):
        SingleLinkableSetting.__init__(self, setting)
        QFrame.__init__(self, parent)

        self.max_ = max_

        label = QLabel(self)
        label.setText(display)
        label.setToolTip(tooltip)
        self.label = label

        slider = Slider(Qt.Horizontal)
        slider.setCursor(QCursor(Qt.PointingHandCursor))
        slider.setFocusPolicy(Qt.ClickFocus)
        slider.setRange(0, max_)
        # max value of max_, avoid errors when the setting is 2147483647 aka inf
        val = min(self.setting_value, max_)
        slider.setValue(val)
        self.slider = slider

        spinbox = self.spin_box()
        spinbox.setRange(0, max_)
        spinbox.setSingleStep(1)
        spinbox.setFixedWidth(120)
        spinbox.setValue(self.setting_value)
        spinbox.setAlignment(Qt.AlignCenter)
        self.spinbox = spinbox
        self.combined = WidgetCombiner(slider, spinbox, self)

        self.slider.valueChanged.connect(lambda val:
            self.on_setting_changed_from_gui(val, set_spinbox=True))
        self.spinbox.valueChanged.connect(self.on_setting_changed_from_gui)

        self.layout = QGridLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.addWidget(label, 0, 0, 1, 1)
        self.layout.addItem(spacer(), 0, 1, 1, 1)
        self.layout.addWidget(self.combined, 0, 2, 1, 3)

        self.setLayout(self.layout)

    def on_setting_changed(self, setting, new_value):
        self.slider.setValue(new_value)
        self.spinbox.setValue(new_value)

    def on_setting_changed_from_gui(self, new_value, set_spinbox=False):
        # if the slider's valueChanged signal is the one that called this
        # function, the spinbox hasn't had its value sycned to the slider yet,
        # so set its value here before performing any operations on it below.
        # This does cause this function to be called twice for each value set
        # from the slider (because when we set the spinbox value it causes
        # another callback to this function) which is a bit wasteful but it's
        # not bad.
        if set_spinbox:
            self.spinbox.setValue(new_value)
        # for some reason the valueChanged signal doesn't call valueFromText
        # and pass that value, but passes the raw underlying value of the
        # spinbox. I'm probably missing something that would make this work
        # automatically but I don't know what. So we force its hand by calling
        # this function manually and overriding what we pass to
        # on_setting_changed_from_gui.
        new_value = self.spinbox.valueFromText(self.spinbox.text())
        super().on_setting_changed_from_gui(new_value)

    def spin_box(self):
        """
        The spinbox to use for this class.
        """
        return QSpinBox()

class SliderBoxMaxInfSetting(SliderBoxSetting):
    """
    a `SliderBoxSetting` which has special behavior when the slider or spinbox
    is at its max value - namely that it sets the associated setting to infinity
    (or an equivalently large value).
    """

    def spin_box(self):
        return SpinBoxMaxInf()

class SpinBoxMaxInf(QSpinBox):

    def textFromValue(self, value):
        if value == self.maximum():
            return "inf"
        return super().textFromValue(value)

    def valueFromText(self, text):
        if text == "inf":
            # can't use `sys.maxsize` because it overflows qt / c's 32bit int
            return 2147483647
        return super().valueFromText(text)


class LineEditSetting(SingleLinkableSetting, QFrame):
    """
    A container class of a QLabel and InputWidget that links the input widget
    to a setting (ie the default value of the widget will be the value of the
    setting, and changes made to the widget will affect the setting).
    """
    def __init__(self, display, tooltip, type_, setting):
        SingleLinkableSetting.__init__(self, setting)
        QFrame.__init__(self)
        self.input_ = InputWidget(display, tooltip, type_=type_)
        self.input_.field.setText(self.setting_value)
        self.input_.field.textChanged.connect(self.on_setting_changed_from_gui)
        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.addWidget(self.input_)
        self.setLayout(self.layout)

    def on_setting_changed(self, setting, new_value):
        self.input_.field.setText(new_value)

class WidgetCombiner(QFrame):
    def __init__(self, widget1, widget2, parent):
        super().__init__(parent)
        # these widgets get created outside of WidgetCombiner and might
        # have had a different parent - but they're our children now!
        widget1.setParent(self)
        widget2.setParent(self)
        self.layout = QGridLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.addWidget(widget1, 0, 0, 1, 1)
        self.layout.addWidget(widget2, 0, 1, 1, 1)
        self.setLayout(self.layout)


class FileChooserButton(PushButton):
    path_chosen_signal = pyqtSignal(Path) # emits the selected path

    def __init__(self, text, file_mode=QFileDialog.AnyFile, name_filters=None):
        super().__init__()
        self.file_mode = file_mode
        self.name_filters = name_filters
        self.selection_made = False
        self.path = None
        self.setText(text)
        self.clicked.connect(self.open_dialog)

    def open_dialog(self):
        """
        Opens a file chooser dialog to the user.
        """
        # regarding #setFileMode and why we don't use it:
        # QFileDialog.ExistingFiles appears to override QFileDialog.Directory,
        # so I don't see a way to support selecting multiple files and selecting
        # directories in the same widget, unless we make our own QDialog class.
        self.dialog = QFileDialog(self)
        self.dialog.setFileMode(self.file_mode)
        if self.name_filters:
            self.dialog.setNameFilters(self.name_filters)
        self.start_dir = self.dialog.directory().absolutePath()

        # recommended over #exec by qt https://doc.qt.io/qt-5/qdialog.html#exec
        self.dialog.open()
        self.dialog.finished.connect(self.process_selection)

    def process_selection(self):
        """
        process whatever the user has chosen (either a folder, file, or
        multiple files).
        """
        # do nothing if the user pressed cancel
        if not self.dialog.result():
            return
        self.selection_made = True
        files = self.dialog.selectedFiles()
        path = files[0]
        path = Path(path)
        self.path = path
        self.path_chosen_signal.emit(path)


class ReplayChooser(QFrame):
    """
    Two FileChoosers (one for files, one for folders), which can select
    .osr files and folders of osr files respectively. Only one can be
    in effect at a time, and the path label shows the latest chosen one.
    """
    def __init__(self):
        super().__init__()
        self.selection_made = False
        self.old_stylesheet = self.styleSheet()
        self.path = None

        self.path_label = QLabel()
        self.path_label.setWordWrap(True)
        self.file_chooser = FileChooserButton("Choose replay", QFileDialog.ExistingFile, ["osu! Replay File (*.osr)"])
        self.folder_chooser = FileChooserButton("Choose folder", QFileDialog.Directory)

        # the buttons will steal the mousePressEvent so connect them manually
        self.file_chooser.clicked.connect(self.reset_required)
        self.folder_chooser.clicked.connect(self.reset_required)
        self.file_chooser.path_chosen_signal.connect(self.handle_new_path)
        self.folder_chooser.path_chosen_signal.connect(self.handle_new_path)

        self.file_chooser.setFixedWidth(185)
        self.folder_chooser.setFixedWidth(185)

        layout = QGridLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.file_chooser, 0, 0, 1, 1)
        layout.addWidget(self.folder_chooser, 0, 1, 1, 1)
        layout.addWidget(self.path_label, 1, 0, 1, 2)
        self.setLayout(layout)

    def handle_new_path(self, path):
        self.path = path
        self.path_label.setText(str(path))
        self.selection_made = self.file_chooser.selection_made or self.folder_chooser.selection_made

    def show_required(self):
        self.setStyleSheet("ReplayChooser { border: 1px solid red; border-radius: 4px; padding: 2px }")

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        self.reset_required()

    def reset_required(self):
        self.setStyleSheet(self.old_stylesheet)



class ResetSettings(QFrame):
    def __init__(self):
        super().__init__()
        self.label = QLabel(self)
        self.label.setText("Reset settings:")

        self.button = PushButton(self)
        self.button.setText("Reset")
        self.button.clicked.connect(self.reset_settings)
        self.button.setFixedWidth(120)

        self.layout = QGridLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.addWidget(self.label, 0, 0, 1, 1)
        self.layout.addItem(spacer(), 0, 1, 1, 1)
        self.layout.addWidget(self.button, 0, 2, 1, 1)
        self.setLayout(self.layout)

    def reset_settings(self):
        prompt = QMessageBox.question(self, "Reset settings",
                        "Are you sure?\n"
                        "This will reset all settings to their default value, "
                        "and the application will quit.",
                        buttons=QMessageBox.No | QMessageBox.Yes,
                        defaultButton=QMessageBox.No)
        if prompt == QMessageBox.Yes:
            reset_defaults()
            QCoreApplication.quit()



class EntryWidget(QFrame):
    """
    Represents a single entry of some kind of data, consisting of a title, a
    button and the data which is stored at self.data.
    When the button is pressed, pressed_signal is emitted with the data.
    """
    pressed_signal = pyqtSignal(object)

    def __init__(self, title, action_name, data):
        super().__init__()
        self.data = data
        self.button = PushButton(action_name)
        self.button.setFixedWidth(100)
        self.button.clicked.connect(self.button_pressed)
        self.layout = QGridLayout()
        self.layout.addWidget(QLabel(title), 0, 0, 1, 1)
        self.layout.addWidget(self.button, 0, 1, 1, 1)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.layout)

    def button_pressed(self, _):
        self.pressed_signal.emit(self.data)
