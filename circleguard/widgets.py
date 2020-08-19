import sys
import ntpath
from pathlib import Path
from functools import partial
import json

from PyQt5.QtWidgets import (QWidget, QFrame, QGridLayout, QLabel, QLineEdit,
    QMessageBox, QSpacerItem, QSizePolicy, QSlider, QSpinBox, QFrame,
QDoubleSpinBox, QFileDialog, QPushButton, QCheckBox, QComboBox, QVBoxLayout,
    QHBoxLayout, QMainWindow, QTableWidget, QTableWidgetItem, QAbstractItemView)
from PyQt5.QtGui import QRegExpValidator, QIcon, QDrag
from PyQt5.QtCore import (QRegExp, Qt, QDir, QCoreApplication, pyqtSignal,
    QPoint, QMimeData)
# from circleguard import Circleguard, TimewarpResult, Mod, Key
# import numpy as np

from settings import (get_setting, reset_defaults, LinkableSetting,
    SingleLinkableSetting, set_setting)
from utils import resource_path, delete_widget, AnalysisResult

SPACER = QSpacerItem(100, 0, QSizePolicy.Maximum, QSizePolicy.Minimum)


# TODO cmd + z doesn't undo operations here, figure out why
class LineEdit(QLineEdit):
    """
    """
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
        self.layout.addItem(SPACER, 0, 1, 1, 1)
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
        self.box = QCheckBox(self)
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
        self.button = QPushButton(button_title)
        self.button.setFixedWidth(120)

        self.layout = QGridLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.addWidget(label, 0, 0, 1, 1)
        self.layout.addItem(SPACER, 0, 1, 1, 1)
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

        combobox = QComboBox(self)
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
        layout.addItem(SPACER, 0, 1, 1, 1)
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


class DropArea(QFrame):
    # style largely taken from
    # https://doc.qt.io/qt-5/qtwidgets-draganddrop-dropsite-example.html
    # (we use a QFrame instead of a QLabel so we can have a layout and
    # add new items to it)
    def __init__(self):
        super().__init__()

        self.loadable_ids = [] # ids of loadables already in this drop area
        self.loadables = [] # LoadableInChecks in this DropArea
        self.setMinimumSize(0, 100)
        self.setFrameStyle(QFrame.Sunken | QFrame.StyledPanel)
        self.setAcceptDrops(True)

        self.layout = QVBoxLayout()
        self.layout.setAlignment(Qt.AlignTop)
        self.setLayout(self.layout)

    def dragEnterEvent(self, event):
        # need to accept the event so qt gives us the DropEvent
        # https://doc.qt.io/qt-5/qdropevent.html#details
        event.acceptProposedAction()

    def dropEvent(self, event):
        mimedata = event.mimeData()
        # don't accept drops from anywhere else
        if not mimedata.hasFormat("application/x-circleguard-loadable"):
            return
        event.acceptProposedAction()
        # second #data necessary to convert QByteArray to python byte array
        data = json.loads(mimedata.data("application/x-circleguard-loadable").data())
        id_ = data[0]
        name = data[1]
        if id_ in self.loadable_ids:
            return
        self.add_loadable(id_, name)

    def add_loadable(self, id_, name):
        self.loadable_ids.append(id_)
        loadable = LoadableInCheck(name + f" (id: {id_})", id_)
        self.layout.addWidget(loadable)
        self.loadables.append(loadable)
        loadable.remove_loadableincheck_signal.connect(self.remove_loadable)

    def remove_loadable(self, loadable_id, loadable_in_check=True):
        """
        loadable_in_check will be True if loadable_id is a LoadableInCheck id,
        otherwise if loadable_in_check is False it is a Loadable id.
        """
        if loadable_in_check:
            loadables = [l for l in self.loadables if l.loadable_in_check_id == loadable_id]
        else:
            loadables = [l for l in self.loadables if l.loadable_id == loadable_id]
        if not loadables:
            return
        loadable = loadables[0]
        self.layout.removeWidget(loadable)
        delete_widget(loadable)
        self.loadables.remove(loadable)
        self.loadable_ids.remove(loadable.loadable_id)

class SingleDropArea(DropArea):
    def add_loadable(self, id_, name):
        if len(self.loadables) == 1:
            return
        super().add_loadable(id_, name)

class CheckW(QFrame):
    remove_check_signal = pyqtSignal(int) # check id
    ID = 0

    def __init__(self, name, double_drop_area=False, single_loadable_drop_area=False):
        super().__init__()
        CheckW.ID += 1
        # so we get the DropEvent
        # https://doc.qt.io/qt-5/qdropevent.html#details
        self.setAcceptDrops(True)
        self.name = name
        self.double_drop_area = double_drop_area
        self.check_id = CheckW.ID
        # will have LoadableW objects added to it once this Check is
        # run by the main tab run button, so that cg.Check objects can
        # be easily constructed with loadables
        if double_drop_area:
            self.loadables1 = []
            self.loadables2 = []
        else:
            self.loadables = []

        self.delete_button = QPushButton(self)
        self.delete_button.setIcon(QIcon(resource_path("delete.png")))
        self.delete_button.setMaximumWidth(30)
        self.delete_button.clicked.connect(partial(lambda check_id: self.remove_check_signal.emit(check_id), self.check_id))
        title = QLabel()
        title.setText(f"{name}")

        self.layout = QGridLayout()
        self.layout.addWidget(title, 0, 0, 1, 7)
        self.layout.addWidget(self.delete_button, 0, 7, 1, 1)
        if double_drop_area:
            self.drop_area1 = DropArea()
            self.drop_area2 = DropArea()
            self.layout.addWidget(self.drop_area1, 1, 0, 1, 4)
            self.layout.addWidget(self.drop_area2, 1, 4, 1, 4)
        else:
            if single_loadable_drop_area:
                self.drop_area = SingleDropArea()
            else:
                self.drop_area = DropArea()
            self.layout.addWidget(self.drop_area, 1, 0, 1, 8)
        self.setLayout(self.layout)

    def remove_loadable(self, loadable_id):
        if self.double_drop_area:
            self.drop_area1.remove_loadable(loadable_id, loadable_in_check=False)
            self.drop_area2.remove_loadable(loadable_id, loadable_in_check=False)
        else:
            self.drop_area.remove_loadable(loadable_id, loadable_in_check=False)

    def all_loadable_ids(self):
        if self.double_drop_area:
            return self.drop_area1.loadable_ids + self.drop_area2.loadable_ids
        return self.drop_area.loadable_ids

    def all_loadables(self):
        if self.double_drop_area:
            return self.loadables1 + self.loadables2
        return self.loadables

class StealCheckW(CheckW):
    def __init__(self):
        super().__init__("Similarity", double_drop_area=True)


class RelaxCheckW(CheckW):
    def __init__(self):
        super().__init__("Unstable Rate")


class CorrectionCheckW(CheckW):
    def __init__(self):
        super().__init__("Snaps")

class TimewarpCheckW(CheckW):
    def __init__(self):
        super().__init__("Frametime")

class AnalyzeW(CheckW):
    def __init__(self):
        super().__init__("Manual Analysis")


class DragWidget(QFrame):
    """
    A widget not meant to be displayed, but rendered into a pixmap with
    #grab and stuck onto a QDrag with setPixmap to give the illusion of
    dragging another widget.
    """
    def __init__(self, text):
        super().__init__()
        self.text = QLabel(text)
        layout = QVBoxLayout()
        layout.addWidget(self.text)
        self.setLayout(layout)


class LoadableInCheck(QFrame):
    """
    Represents a LoadableW inside a CheckW.
    """
    remove_loadableincheck_signal = pyqtSignal(int)
    ID = 0
    def __init__(self, text, loadable_id):
        super().__init__()
        LoadableInCheck.ID += 1
        self.text = QLabel(text)
        self.loadable_in_check_id = LoadableInCheck.ID
        self.loadable_id = loadable_id

        self.delete_button = QPushButton(self)
        self.delete_button.setIcon(QIcon(resource_path("delete.png")))
        self.delete_button.setMaximumWidth(30)
        self.delete_button.clicked.connect(partial(lambda id_: self.remove_loadableincheck_signal.emit(id_), self.loadable_in_check_id))

        self.layout = QGridLayout()
        self.layout.addWidget(self.text, 0, 0, 1, 7)
        self.layout.addWidget(self.delete_button, 0, 7, 1, 1)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.layout)


class LoadableW(QFrame):
    """
    A widget representing a circleguard.Loadable, which can be dragged onto
    a CheckW. Keeps track of how many LoadableWs have been created
    as a static ID attribute.

    W standing for widget.
    """
    ID = 0
    remove_loadable_signal = pyqtSignal(int) # id of loadable to remove

    def __init__(self, name, required_input_widgets):
        super().__init__()
        LoadableW.ID += 1
        self.name = name
        self.required_input_widgets = required_input_widgets

        self.layout = QGridLayout()
        title = QLabel(self)
        self.loadable_id = LoadableW.ID
        t = "\t" # https://stackoverflow.com/a/44780467/
        # double tabs on short names to align with longer ones
        title.setText(f"{name}{t+t if len(name) < 5 else t}(id: {self.loadable_id})")

        self.delete_button = QPushButton(self)
        self.delete_button.setIcon(QIcon(resource_path("delete.png")))
        self.delete_button.setMaximumWidth(30)
        self.delete_button.clicked.connect(partial(lambda loadable_id: self.remove_loadable_signal.emit(loadable_id), self.loadable_id))
        self.layout.addWidget(title, 0, 0, 1, 7)
        self.layout.addWidget(self.delete_button, 0, 7, 1, 1)
        self.setLayout(self.layout)

    # Resources for drag and drop operations:
    # qt tutorial           https://doc.qt.io/qt-5/qtwidgets-draganddrop-draggableicons-example.html
    # qdrag docs            https://doc.qt.io/qt-5/qdrag.html
    # real example code     https://lists.qt-project.org/pipermail/qt-interest-old/2011-June/034531.html
    # bad example code      https://stackoverflow.com/q/7737913/
    def mouseMoveEvent(self, event):
        # 1=all the way to the right/down, 0=all the way to the left/up
        x_ratio = event.pos().x() / self.width()
        y_ratio = event.pos().y() / self.height()
        self.drag = QDrag(self)
        # https://stackoverflow.com/a/53538805/
        pixmap = DragWidget(f"{self.name} (Id: {self.loadable_id})").grab()
        # put cursor in the same relative position on the dragwidget as
        # it clicked on the real Loadable widget.
        self.drag.setHotSpot(QPoint(pixmap.width() * x_ratio, pixmap.height() * y_ratio))
        self.drag.setPixmap(pixmap)
        mime_data = QMimeData()
        data = [self.loadable_id, self.name]
        mime_data.setData("application/x-circleguard-loadable", bytes(json.dumps(data), "utf-8"))
        self.drag.setMimeData(mime_data)
        self.drag.exec() # start the drag

    def check_required_fields(self):
        """
        Checks the required fields of this LoadableW. If any are empty, show
        a red border around them (see InputWidget#show_required) and return
        False. Otherwise, return True.
        """
        all_filled = True
        for input_widget in self.required_input_widgets:
            # don't count inputs with defaults as empty
            filled = input_widget.value() != "" or input_widget.field.placeholderText() != ""
            if not filled:
                input_widget.show_required()
                all_filled = False
        return all_filled

class ReplayMapW(LoadableW):
    """
    W standing for Widget.
    """
    def __init__(self):
        self.map_id_input = InputWidget("Map id", "", "id")
        self.user_id_input = InputWidget("User id", "", "id")
        self.mods_input = InputWidget("Mods (opt.)", "", "normal")

        super().__init__("Map Replay", [self.map_id_input, self.user_id_input])

        self.layout.addWidget(self.map_id_input, 1, 0, 1, 8)
        self.layout.addWidget(self.user_id_input, 2, 0, 1, 8)
        self.layout.addWidget(self.mods_input, 3, 0, 1, 8)


class ReplayPathW(LoadableW):
    def __init__(self):
        self.path_input = ReplayChooser()
        super().__init__("Local Replay", [self.path_input])

        self.layout.addWidget(self.path_input, 1, 0, 1, 8)

    def check_required_fields(self):
        all_filled = True
        for input_widget in self.required_input_widgets:
            filled = input_widget.selection_made
            if not filled:
                input_widget.show_required()
                all_filled = False
        return all_filled

class MapW(LoadableW):
    def __init__(self):

        self.map_id_input = InputWidget("Map id", "", "id")
        self.span_input = InputWidget("Span", "", "normal")
        self.span_input.field.setPlaceholderText(get_setting("default_span_map"))
        self.mods_input = InputWidget("Mods (opt.)", "", "normal")

        super().__init__("Map", [self.map_id_input, self.span_input])

        self.layout.addWidget(self.map_id_input, 1, 0, 1, 8)
        self.layout.addWidget(self.span_input, 2, 0, 1, 8)
        self.layout.addWidget(self.mods_input, 3, 0, 1, 8)

class UserW(LoadableW):
    def __init__(self):

        self.user_id_input = InputWidget("User id", "", "id")
        self.span_input = InputWidget("Span", "", "normal")
        self.mods_input = InputWidget("Mods (opt.)", "", "normal")
        self.span_input.field.setPlaceholderText(get_setting("default_span_user"))

        super().__init__("User", [self.user_id_input, self.span_input])

        self.layout.addWidget(self.user_id_input, 1, 0, 1, 8)
        self.layout.addWidget(self.span_input, 2, 0, 1, 8)
        self.layout.addWidget(self.mods_input, 3, 0, 1, 8)


class MapUserW(LoadableW):
    def __init__(self):
        self.map_id_input = InputWidget("Map id", "", "id")
        self.user_id_input = InputWidget("User id", "", "id")
        self.span_input = InputWidget("Span", "", "normal")
        self.span_input.field.setPlaceholderText("all")

        super().__init__("All Map Replays by User", [self.map_id_input, self.user_id_input, self.span_input])

        self.layout.addWidget(self.map_id_input, 1, 0, 1, 8)
        self.layout.addWidget(self.user_id_input, 2, 0, 1, 8)
        self.layout.addWidget(self.span_input, 3, 0, 1, 8)


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
        self.visualize_button = QPushButton(self)
        self.visualize_button.setText("Visualize")
        self.visualize_button.clicked.connect(lambda: self.visualize_button_pressed_signal.emit())

        if len(replays) == 1:
            self.set_layout_single()
        # at the moment, this only happens for replay stealing and when
        # visualizing multiple replays
        else:
            self.set_layout_multiple()

    def set_layout_single(self):
        self.actions_combobox = QComboBox()
        self.actions_combobox.addItem("More")
        self.actions_combobox.addItem("View Frametimes", "View Frametimes")
        self.actions_combobox.addItem("View Replay Data", "View Replay Data")
        self.actions_combobox.setInsertPolicy(QComboBox.NoInsert)
        self.actions_combobox.activated.connect(self.action_combobox_activated)

        layout = QGridLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.label, 0, 0, 1, 4)
        layout.addItem(SPACER, 0, 4, 1, 1)
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
        layout.addItem(SPACER, 0, 1, 1, 1)
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
        template_button = QPushButton(self)
        template_button.setText("Copy Template")
        template_button.clicked.connect(lambda: self.template_button_pressed_signal.emit())
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
    # for any frametimes larger than this, chuck them into a single bin.
    # matplotlib can't really handle that many bins otherwise
    MAX_FRAMETIME = 50

    def __init__(self, result, replay):
        super().__init__()
        from circleguard import TimewarpResult
        from matplotlib.backends.backend_qt5agg import FigureCanvas # pylint: disable=no-name-in-module
        from matplotlib.figure import Figure

        frametimes = None
        self.show_cv = get_setting("frametime_graph_display") == "cv"
        self.conversion_factor = self._conversion_factor(replay)
        if isinstance(result, TimewarpResult):
            frametimes = result.frametimes
        else:
            # just recalulate from circleguard, replay is already loaded so
            # this should be fast
            frametimes = self.get_frametimes(replay)

        # figsize is in inches for whatever reason lol
        self.canvas = FigureCanvas(Figure(figsize=(5, 5)))
        self.canvas.figure.suptitle(f"({'cv' if self.show_cv else 'ucv'}) Frametime Histogram")

        self.max_frametime = max(frametimes)
        if self.max_frametime > self.MAX_FRAMETIME:
            self.plot_with_break(frametimes)
        else:
            self.plot_normal(frametimes)

        layout = QVBoxLayout()
        layout.addWidget(self.canvas)
        self.setLayout(layout)


    def plot_normal(self, frametimes):
        import numpy as np
        frametimes = self.conversion_factor * frametimes
        ax = self.canvas.figure.subplots()

        bins = np.arange(0, (self.conversion_factor * self.max_frametime) + 1, self.conversion_factor)
        ax.hist(frametimes, bins)
        ax.set_xlabel("Frametime")
        ax.set_ylabel("Count")

    # adapted from https://matplotlib.org/examples/pylab_examples/broken_axis.html
    def plot_with_break(self, frametimes):
        import numpy as np
        # gridspec_kw to make outlier plot smaller than the main one. https://stackoverflow.com/a/35881382
        ax1, ax2 = self.canvas.figure.subplots(1, 2, sharey=True, gridspec_kw={"width_ratios": [3, 1]})
        ax1.spines["right"].set_visible(False)
        ax2.spines["left"].set_visible(False)
        ax1.set_xlabel("Frametime")
        ax1.set_ylabel("Count")

        ax2.tick_params(left=False)

        low_frametime_truth_arr = frametimes <= self.MAX_FRAMETIME
        low_frametimes = frametimes[low_frametime_truth_arr]
        high_frametimes = frametimes[~low_frametime_truth_arr]

        low_frametimes = self.conversion_factor * low_frametimes
        high_frametimes = self.conversion_factor * high_frametimes

        bins = np.arange(0, (self.conversion_factor * self.MAX_FRAMETIME) + 1, self.conversion_factor)
        ax1.hist(low_frametimes, bins)
        # -1 in case high_frametimes has only one frame
        bins = [(self.conversion_factor * min(high_frametimes)) - 1, self.conversion_factor * self.max_frametime]
        ax2.hist(high_frametimes, bins)

    # the way we deal with cv / ucv is a mess currently because some things need
    # to be converted sometimes and not others and I just didn't want to deal
    # with the headache of abstraction. I'm sure a clean way to do this exists,
    # but the messy solution will work for now.

    def _conversion_factor(self, replay):
        from circleguard import Mod
        if not self.show_cv:
            return 1
        if Mod.DT in replay.mods:
            return 1 / 1.5
        if Mod.HT in replay.mods:
            return 1 / 0.75
        return 1

    @classmethod
    def get_frametimes(self, replay):
        from circleguard import Circleguard
        cg = Circleguard(get_setting("api_key"))
        result = list(cg.timewarp_check(replay))
        return result[0].frametimes

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
            item = QTableWidgetItem(str(t))
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
        self.text = f"Run with {len(run.checks)} Checks"
        self.label.setText(self.text)

        self.status_label = QLabel(self)
        self.status_label.setText("<b>Status: " + self.status + "</b>")
        self.status_label.setTextFormat(Qt.RichText) # so we can bold it
        self.button = QPushButton(self)
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

        slider = QSlider(Qt.Horizontal)
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

        self.slider.valueChanged.connect(self.on_setting_changed_from_gui)
        self.spinbox.valueChanged.connect(self.on_setting_changed_from_gui)

        self.layout = QGridLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.addWidget(label, 0, 0, 1, 1)
        self.layout.addItem(SPACER, 0, 1, 1, 1)
        self.layout.addWidget(self.combined, 0, 2, 1, 3)

        self.setLayout(self.layout)

    def on_setting_changed(self, setting, new_value):
        self.slider.setValue(new_value)
        self.spinbox.setValue(new_value)

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
        super(WidgetCombiner, self).__init__(parent)
        # these widgets get created outside of WidgetCombiner and might
        # have had a different parent - but they're our children now!
        widget1.setParent(self)
        widget2.setParent(self)
        self.layout = QGridLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.addWidget(widget1, 0, 0, 1, 1)
        self.layout.addWidget(widget2, 0, 1, 1, 1)
        self.setLayout(self.layout)


class FileChooserButton(QPushButton):
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
        files = self.dialog.selectedFiles()
        # will only be 1 file at most, but could be 0 (if the user canceled)
        if not files:
            self.selection_made = False
            return
        path = files[0]
        self.selection_made = path != self.start_dir

        # TODO truncate path, ideally with qt size policies but might not be
        # possible with those alone
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
        self.path_label = QLabel()
        self.selection_made = False
        self.old_stylesheet = self.styleSheet()
        self.path = None
        # give all space to the label
        expanding = QSizePolicy()
        expanding.setHorizontalPolicy(QSizePolicy.Expanding)
        self.path_label.setSizePolicy(expanding)
        self.file_chooser = FileChooserButton("Choose replay", QFileDialog.ExistingFile, ["osu! Replay File (*.osr)"])
        self.folder_chooser = FileChooserButton("Choose folder", QFileDialog.Directory)

        # the buttons will steal the mousePressEvent so connect them manually
        self.file_chooser.clicked.connect(self.reset_required)
        self.folder_chooser.clicked.connect(self.reset_required)

        self.file_chooser.path_chosen_signal.connect(self.handle_new_path)
        self.folder_chooser.path_chosen_signal.connect(self.handle_new_path)

        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.path_label)
        layout.addWidget(self.file_chooser)
        layout.addWidget(self.folder_chooser)
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


class BeatmapChooser(FileChooserButton):
    """
    A FileChooser which can only select a single .osu file.
    """
    def __init__(self, text):
        super().__init__(text, file_mode=QFileDialog.ExistingFile, name_filters=["osu! Beatmap File (*.osu)"])


class FolderChooser(QFrame):
    path_signal = pyqtSignal(object) # an iterable if multiple_files is True, str otherwise

    def __init__(self, title, path=str(Path.home()), folder_mode=True, multiple_files=False, file_ending="osu! Beatmapfile (*.osu)", display_path=True):
        super(FolderChooser, self).__init__()
        self.highlighted = False
        # if the selection currently differs from the default path
        self.changed = False
        self.default_path = path
        self.path = path
        self.display_path = display_path
        self.folder_mode = folder_mode
        self.multiple_files = multiple_files
        self.file_ending = file_ending
        self.label = QLabel(self)
        self.label.setText(title + ":")

        self.file_chooser_button = QPushButton(self)
        type_ = "Folder" if self.folder_mode else "Files" if self.multiple_files else "File"
        self.file_chooser_button.setText("Choose " + type_)
        # if we didn't have this line only clicking on the label would unhighlight,
        # since the button steals the mouse clicked event
        self.file_chooser_button.clicked.connect(self.reset_highlight)
        self.file_chooser_button.clicked.connect(self.set_dir)

        self.file_chooser_button.setFixedWidth(120)

        self.path_label = QLabel(self)
        if self.display_path:
            self.path_label.setText(path)
        self.combined = WidgetCombiner(self.path_label, self.file_chooser_button, self)
        # for mousePressedEvent / show_required
        self.old_stylesheet = self.combined.styleSheet()

        self.layout = QGridLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.addWidget(self.label, 0, 0, 1, 1)
        self.layout.addItem(SPACER, 0, 1, 1, 1)
        self.layout.addWidget(self.combined, 0, 2, 1, 3)
        self.setLayout(self.layout)

    def set_dir(self):
        parent_path_old = self.path if self.folder_mode else str(Path(self.path[0]).parent)
        if self.folder_mode:
            options = QFileDialog.Option()
            options |= QFileDialog.ShowDirsOnly
            options |= QFileDialog.HideNameFilterDetails
            update_path = QFileDialog.getExistingDirectory(caption="Select Folder", directory=parent_path_old, options=options)
        elif self.multiple_files:
            paths = QFileDialog.getOpenFileNames(caption="Select Files", directory=parent_path_old, filter=self.file_ending)
            # qt returns a list of ([path, path, ...], filter) when we use a filter
            update_path = paths[0]
        else:
            paths = QFileDialog.getOpenFileName(caption="Select File", directory=parent_path_old, filter=self.file_ending)
            update_path = paths[0]

        # dont update path if cancel is pressed
        if update_path != [] and update_path != "":
            self.update_dir(update_path)

    def update_dir(self, path):
        self.path = path if path != "" else self.path
        self.changed = True if self.path != self.default_path else False
        if self.display_path:
            if self.multiple_files:
                label = str(Path(self.path).parent)
            elif self.folder_mode:
                label = str(self.path)
            else:
                label = str(ntpath.basename(self.path))
            label = label[:50] + '...' if len(label) > 50 else label
            self.path_label.setText(label)
        self.path_signal.emit(self.path)

    def show_required(self):
        self.combined.setStyleSheet(get_setting("required_style"))
        self.highlighted = True

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        self.reset_highlight()

    # separate function so we can call this method outside of mousePressEvent
    def reset_highlight(self):
        if self.highlighted:
            self.combined.setStyleSheet(self.old_stylesheet)
            self.highlighted = False


class ResetSettings(QFrame):
    def __init__(self):
        super(ResetSettings, self).__init__()
        self.label = QLabel(self)
        self.label.setText("Reset settings:")

        self.button = QPushButton(self)
        self.button.setText("Reset")
        self.button.clicked.connect(self.reset_settings)
        self.button.setFixedWidth(120)

        self.layout = QGridLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.addWidget(self.label, 0, 0, 1, 1)
        self.layout.addItem(SPACER, 0, 1, 1, 1)
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


class BeatmapTest(QFrame):
    def __init__(self):
        super(BeatmapTest, self).__init__()
        self.visualizer_window = None

        self.file_chooser = BeatmapChooser("Choose beatmap")
        self.file_chooser.setFixedWidth(120)
        file_chooser_label = QLabel("Beatmap file:", self)

        visualize_label = QLabel("Visualize beatmap:", self)
        self.visualize_button = QPushButton("Visualize", self)
        self.visualize_button.setFixedWidth(120)

        layout = QGridLayout()

        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(file_chooser_label, 0, 0, 1, 1)
        layout.addItem(SPACER, 0, 1, 1, 1)
        layout.addWidget(self.file_chooser, 0, 2, 1, 1)

        layout.addWidget(visualize_label, 1, 0, 1, 1)
        layout.addItem(SPACER, 1, 1, 1, 1)
        layout.addWidget(self.visualize_button, 1, 2, 1, 1)
        self.setLayout(layout)


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
        self.button = QPushButton(action_name)
        self.button.setFixedWidth(100)
        self.button.clicked.connect(self.button_pressed)
        self.layout = QGridLayout()
        self.layout.addWidget(QLabel(title), 0, 0, 1, 1)
        self.layout.addWidget(self.button, 0, 1, 1, 1)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.layout)

    def button_pressed(self, _):
        self.pressed_signal.emit(self.data)
