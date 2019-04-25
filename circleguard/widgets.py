# pylint: disable=no-name-in-module
from functools import partial
from PyQt5.QtWidgets import (QWidget, QGridLayout, QLabel, QLineEdit,
                             QSpacerItem, QSizePolicy, QSlider, QSpinBox,
                             QDoubleSpinBox, QFileDialog, QPushButton, QCheckBox)
from PyQt5.QtGui import QRegExpValidator
from PyQt5.QtCore import QRegExp, Qt, QDir, QCoreApplication, pyqtSignal
# pylint: enable=no-name-in-module
from settings import THRESHOLD
# pylint: disable=no-name-in-module

SPACER = QSpacerItem(100, 0, QSizePolicy.Maximum, QSizePolicy.Minimum)


def set_event_window(window):
    """
    To emulate key presses, we need a window to send the keypress to.
    This main window is created in gui.pyw, so we need to set it here as well.
    """
    global WINDOW
    WINDOW = window


class IDLineEdit(QLineEdit):
    r"""
    A QLineEdit that does not allow anything but digits to be entered.
    Specifically, anything not matched by the \d* regex is not registered.

    This class also overrides the keyPressEvent to allow the left and right
    keys to be sent to our window that controls shortcuts, instead of being used only by the LineEdit.
    """

    def __init__(self, parent):
        super(IDLineEdit, self).__init__(parent)
        # r prefix isn't necessary but pylint was annoying
        validator = QRegExpValidator(QRegExp(r"\d*"))
        self.setValidator(validator)

    def keyPressEvent(self, event):
        key = event.key()
        if key == Qt.Key_Left or key == Qt.Key_Right:
            QCoreApplication.sendEvent(WINDOW, event)
        super().keyPressEvent(event)


class LineEdit(QLineEdit):
    r"""
    A QLineEdit that overrides the keyPressEvent to allow the left and right
    keys to be sent to our window that controls shortcuts, instead of being used only by the LineEdit.
    """

    def keyPressEvent(self, event):
        key = event.key()
        if key == Qt.Key_Left or key == Qt.Key_Right:
            QCoreApplication.sendEvent(WINDOW, event)
        super().keyPressEvent(event)


class SpinBox(QSpinBox):
    """
    A QSpinBox that overrides the keyPressEvent to allow the left and right
    keys to be sent to our window that controls shortcuts, instead of being used only by the SpinBox.
    """

    def keyPressEvent(self, event):
        key = event.key()
        if key == Qt.Key_Left or key == Qt.Key_Right:
            QCoreApplication.sendEvent(WINDOW, event)
        super().keyPressEvent(event)


class DoubleSpinBox(QDoubleSpinBox):
    """
    A QDoubleSpinBox that overrides the keyPressEvent to allow the left and right
    keys to be sent to our window that controls shortcuts, instead of being used only by the DoubleSpinBox.
    """

    def keyPressEvent(self, event):
        key = event.key()
        if key == Qt.Key_Left or key == Qt.Key_Right:
            QCoreApplication.sendEvent(WINDOW, event)
        super().keyPressEvent(event)


class IdWidget(QWidget):
    """
    A container class of widgets that represents user input for an id. This class
    holds a Label and IDLineEdit.
    """

    def __init__(self, title, tooltip):
        super(IdWidget, self).__init__()

        label = QLabel(self)
        label.setText(title+":")
        label.setToolTip(tooltip)
        self.field = IDLineEdit(self)

        layout = QGridLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(label, 0, 0, 1, 1)
        layout.addItem(SPACER, 0, 1, 1, 1)
        layout.addWidget(self.field, 0, 2, 1, 3)
        self.setLayout(layout)


class IdWidgetCombined(QWidget):
    """
    A container class of widgets that represents user input for a map id and user id.
    If no map id is given the user id field will be disabled.

    This class holds 2 rows of a Label and IDLineEdit.
    """

    def __init__(self):
        super(IdWidgetCombined, self).__init__()

        map_label = QLabel(self)
        map_label.setText("Map Id:")
        map_label.setToolTip("Beatmap id, not the mapset id!")
        self.map_label = map_label
        self.map_field = IDLineEdit(self)
        self.map_field.textChanged.connect(self.update_user)

        user_label = QLabel(self)
        user_label.setText("User Id:")
        user_label.setToolTip("User id, as seen in the profile url")
        self.user_label = user_label
        self.user_field = IDLineEdit(self)

        self.update_user()

        layout = QGridLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(map_label, 0, 0, 1, 1)
        layout.addItem(SPACER, 0, 1, 1, 1)
        layout.addWidget(self.map_field, 0, 2, 1, 3)
        layout.addWidget(user_label, 1, 0, 1, 1)
        layout.addItem(SPACER, 1, 1, 1, 1)
        layout.addWidget(self.user_field, 1, 2, 1, 3)
        self.setLayout(layout)

    def update_user(self):
        self.user_field.setEnabled(self.map_field.text() != "")


class InputWidget(QWidget):
    """
    A container class of widgets that represents user input. This class
    holds a Label and LineEdit.
    """

    def __init__(self, title, tooltip):
        super(InputWidget, self).__init__()

        label = QLabel(self)
        label.setText(title+":")
        label.setToolTip(tooltip)
        self.field = LineEdit(self)

        layout = QGridLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(label, 0, 0, 1, 1)
        layout.addItem(SPACER, 0, 1, 1, 1)
        layout.addWidget(self.field, 0, 2, 1, 3)
        self.setLayout(layout)


class OptionWidget(QWidget):
    """
    A container class of widgets that represents an option with an disabled/enabled state.
    This class holds a Label and CheckBox.
    """

    def __init__(self, title, tooltip):
        super(OptionWidget, self).__init__()

        label = QLabel(self)
        label.setText(title+":")
        label.setToolTip(tooltip)
        self.box = QCheckBox(self)

        layout = QGridLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(label, 0, 0, 1, 1)
        layout.addItem(SPACER, 0, 1, 1, 1)
        layout.addWidget(self.box, 0, 2, 1, 3)
        self.setLayout(layout)


class CompareTopUsers(QWidget):
    """
    A container class of widgets that represents user input for how many users of a map to compare.
    This class holds a Label, Slider, and SpinBox.

    This class includes a function which is meant to disable/enable the Slider and SpinBox externally.
    The SpinBox and Slider are linked internally by this class, so when one changes, so does the other.
    """

    def __init__(self):
        super(CompareTopUsers, self).__init__()
        self.label = QLabel(self)
        self.label.setText("Compare Top Users:")
        self.label.setToolTip("Compare this many plays from the leaderboard")

        slider = QSlider(Qt.Horizontal)
        slider.setMinimum(2)
        slider.setMaximum(100)
        slider.setValue(50)
        slider.valueChanged.connect(self.update_spinbox)
        self.slider = slider

        spinbox = SpinBox(self)
        spinbox.setValue(50)
        spinbox.setAlignment(Qt.AlignCenter)
        spinbox.setRange(2, 100)
        spinbox.setSingleStep(1)
        spinbox.valueChanged.connect(self.update_slider)
        self.spinbox = spinbox

        layout = QGridLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.label, 0, 0, 1, 1)
        layout.addItem(SPACER, 0, 1, 1, 1)
        layout.addWidget(self.slider, 0, 2, 1, 2)
        layout.addWidget(self.spinbox, 0, 4, 1, 1)
        self.setLayout(layout)

    # keep spinbox and slider in sync
    def update_spinbox(self, value):
        self.spinbox.setValue(value)

    def update_slider(self, value):
        self.slider.setValue(value)

    def update_user(self, mode):
        self.slider.setEnabled(False if not mode else True)
        self.spinbox.setEnabled(False if not mode else True)


class CompareTopPlays(QWidget):
    """
    A container class of widgets that represents user input for how many top plays of a user to compare.
    This class holds a Label, Slider, and SpinBox.

    The SpinBox and Slider are linked internally by this class, so when one changes, so does the other.
    """

    def __init__(self):
        super(CompareTopPlays, self).__init__()
        label = QLabel(self)
        label.setText("Compare Top Plays:")
        label.setToolTip("Compare this many plays from the leaderboard")

        slider = QSlider(Qt.Horizontal)
        slider.setValue(20)
        slider.setMinimum(1)
        slider.setMaximum(100)
        slider.valueChanged.connect(self.update_spinbox)
        self.slider = slider

        spinbox = SpinBox(self)
        spinbox.setValue(20)
        spinbox.setAlignment(Qt.AlignCenter)
        spinbox.setRange(2, 100)
        spinbox.setSingleStep(1)
        spinbox.valueChanged.connect(self.update_slider)
        self.spinbox = spinbox

        layout = QGridLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(label, 0, 0, 1, 1)
        layout.addItem(SPACER, 0, 1, 1, 1)
        layout.addWidget(slider, 0, 2, 1, 2)
        layout.addWidget(spinbox, 0, 4, 1, 1)
        self.setLayout(layout)

    # keep spinbox and slider in sync
    def update_spinbox(self, value):
        self.spinbox.setValue(value)

    def update_slider(self, value):
        self.slider.setValue(value)


class ThresholdCombined(QWidget):
    """
    A container class of widgets that represents user input for the threshold/auto threshold
    to consider a comparison a cheat.
    This class holds 2 rows of a Label, Slider, and SpinBox.

    The SpinBox and Slider are linked internally by this class (once for the threshold and once for the auto threshold),
    so when one changes, so does the other.
    """

    def __init__(self):
        super(ThresholdCombined, self).__init__()

        thresh_label = QLabel(self)
        thresh_label.setText("Threshold:")
        thresh_label.setToolTip("Cutoff for how similar two replays must be to be printed")
        self.thresh_label = thresh_label

        thresh_slider = QSlider(Qt.Horizontal)
        thresh_slider.setRange(0, 30)
        thresh_slider.setValue(THRESHOLD)
        thresh_slider.valueChanged.connect(self.update_thresh_spinbox)
        self.thresh_slider = thresh_slider

        thresh_spinbox = SpinBox(self)
        thresh_spinbox.setValue(THRESHOLD)
        thresh_spinbox.setAlignment(Qt.AlignCenter)
        thresh_spinbox.setRange(0, 30)
        thresh_spinbox.setSingleStep(1)
        thresh_spinbox.valueChanged.connect(self.update_thresh_slider)
        self.thresh_spinbox = thresh_spinbox
        self.thresh_spinbox.valueChanged.connect(partial(self.switch_thresh, 0))

        autothresh_label = QLabel(self)
        autothresh_label.setText("Auto Threshold:")
        autothresh_label.setToolTip("Stddevs below average threshold to print for" +
                                    "\n(typically between TLS and 2.5. The higher, the less results you will get)")
        self.autothresh_label = autothresh_label

        autothresh_slider = QSlider(Qt.Horizontal)
        autothresh_slider.setRange(10, 30)
        autothresh_slider.setValue(20)
        autothresh_slider.valueChanged.connect(self.update_autothresh_spinbox)
        self.autothresh_slider = autothresh_slider

        autothresh_slider = QSlider(Qt.Horizontal)
        autothresh_slider.setRange(10, 30)
        autothresh_slider.setValue(20)
        autothresh_slider.valueChanged.connect(self.update_autothresh_spinbox)
        self.autothresh_slider = autothresh_slider

        autothresh_spinbox = DoubleSpinBox(self)
        autothresh_spinbox.setValue(2.0)
        autothresh_spinbox.setAlignment(Qt.AlignCenter)
        autothresh_spinbox.setRange(1.0, 3.0)
        autothresh_spinbox.setSingleStep(0.1)
        autothresh_spinbox.valueChanged.connect(self.update_autothresh_slider)
        self.autothresh_spinbox = autothresh_spinbox
        self.autothresh_spinbox.valueChanged.connect(partial(self.switch_thresh, 1))

        layout = QGridLayout()
        layout.setContentsMargins(0, 0, 0, 0)

        layout.addWidget(thresh_label, 0, 0, 1, 1)
        layout.addItem(SPACER, 0, 1, 1, 1)
        layout.addWidget(thresh_slider, 0, 2, 1, 2)
        layout.addWidget(thresh_spinbox, 0, 4, 1, 1)

        layout.addWidget(autothresh_label, 1, 0, 1, 1)
        layout.addItem(SPACER, 1, 1, 1, 1)
        layout.addWidget(autothresh_slider, 1, 2, 1, 2)
        layout.addWidget(autothresh_spinbox, 1, 4, 1, 1)

        self.setLayout(layout)
        self.switch_thresh(0)

    # keep spinbox and slider in sync
    def update_thresh_spinbox(self, value):
        self.thresh_spinbox.setValue(value)

    def update_thresh_slider(self, value):
        self.thresh_slider.setValue(value)

    def update_autothresh_spinbox(self, value):
        self.autothresh_spinbox.setValue(value/10)

    def update_autothresh_slider(self, value):
        self.autothresh_slider.setValue(value*10)

    def switch_thresh(self, state):
        self.thresh_label.setStyleSheet("color: gray" if state else "")
        self.thresh_spinbox.setStyleSheet("color: gray" if state else "")
        self.autothresh_label.setStyleSheet("color: gray" if not state else "")
        self.autothresh_spinbox.setStyleSheet("color: gray" if not state else "")


class Threshold(QWidget):
    """
    A container class of widgets that represents user input for the threshold to consider a comparison a cheat.
    This widget is meant to be used in cases where Auto Threshold is not needed, else use ThresholdCombined.
    This class holds a Label, Slider, and SpinBox.

    The SpinBox and Slider are linked internally by this class, so when one changes, so does the other.
    """

    def __init__(self, prefix=""):
        super(Threshold, self).__init__()

        thresh_label = QLabel(self)
        thresh_label.setText(prefix + "Threshold:")
        thresh_label.setToolTip("Cutoff for how similar two replays must be to be printed")
        self.thresh_label = thresh_label

        thresh_slider = QSlider(Qt.Horizontal)
        thresh_slider.setRange(0, 30)
        thresh_slider.setValue(THRESHOLD)
        thresh_slider.valueChanged.connect(self.update_thresh_spinbox)
        self.thresh_slider = thresh_slider

        thresh_spinbox = SpinBox(self)
        thresh_spinbox.setValue(THRESHOLD)
        thresh_spinbox.setAlignment(Qt.AlignCenter)
        thresh_spinbox.setRange(0, 30)
        thresh_spinbox.setSingleStep(1)
        thresh_spinbox.valueChanged.connect(self.update_thresh_slider)
        self.thresh_spinbox = thresh_spinbox

        layout = QGridLayout()
        layout.setContentsMargins(0, 0, 0, 0)

        layout.addWidget(thresh_label, 0, 0, 1, 1)
        layout.addItem(SPACER, 0, 1, 1, 1)
        layout.addWidget(thresh_slider, 0, 2, 1, 2)
        layout.addWidget(thresh_spinbox, 0, 4, 1, 1)

        self.setLayout(layout)

    # keep spinbox and slider in sync
    def update_thresh_spinbox(self, value):
        self.thresh_spinbox.setValue(value)

    def update_thresh_slider(self, value):
        self.thresh_slider.setValue(value)


class FolderChoose(QWidget):
    path_signal = pyqtSignal(str)

    def __init__(self, title):
        super(FolderChoose, self).__init__()
        self.path = ""
        label = QLabel(self)
        label.setText(title+":")

        self.file_chooser = QPushButton(self)
        self.file_chooser.setText("Choose Folder")
        self.file_chooser.pressed.connect(self.set_dir)

        self.path_label = QLabel(self)
        self.path_label.setText("")

        layout = QGridLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(label, 0, 0, 1, 1)
        layout.addItem(SPACER, 0, 1, 1, 1)
        layout.addWidget(self.path_label, 0, 2, 1, 2)
        layout.addWidget(self.file_chooser, 0, 4, 1, 1)
        self.setLayout(layout)

    def set_dir(self):
        options = QFileDialog.Option()
        options |= QFileDialog.ShowDirsOnly
        options |= QFileDialog.HideNameFilterDetails
        tmp = QFileDialog.getExistingDirectory(caption="Select Output Folder", directory=QDir.currentPath(), options=options)
        self.update_dir(tmp)

    def update_dir(self, tmp):
        self.path = tmp if tmp != "" else self.path
        self.path_label.setText(self.path)
        self.dir_updated()

    def dir_updated(self):
        self.path_signal.emit(self.path)
