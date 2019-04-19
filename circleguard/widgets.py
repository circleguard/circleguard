# pylint: disable=no-name-in-module
from PyQt5.QtWidgets import (QWidget, QGridLayout, QLabel, QLineEdit,
                             QSpacerItem, QSizePolicy, QSlider, QSpinBox,
                             QDoubleSpinBox, QFileDialog, QPushButton)
from PyQt5.QtGui import QRegExpValidator
from PyQt5.QtCore import QRegExp, Qt, QSettings, QDir, QCoreApplication
# pylint: enable=no-name-in-module
from functools import partial
from settings import THRESHOLD

spacer = QSpacerItem(100, 0, QSizePolicy.Maximum, QSizePolicy.Minimum)


def set_event_window(window):
    """
    To emulate keypresses, we need a window to send the keypress to.
    This main window is created in gui.pyw, so we need to set it here as well.
    """
    global WINDOW
    WINDOW = window


class IDLineEdit(QLineEdit):
    r"""
    A LineEdit that does not allow anything but digits to be entered.
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


class SpinBox(QSpinBox):
    """
    A SpinBox that overrides the keyPressEvent to allow the left and right
    keys to be sent to our window that controls shortcuts, instead of being used only by the SpinBox.
    """

    def __init__(self, parent):
        super(SpinBox, self).__init__(parent)

    def keyPressEvent(self, event):
        key = event.key()
        if key == Qt.Key_Left or key == Qt.Key_Right:
            QCoreApplication.sendEvent(WINDOW, event)
        super().keyPressEvent(event)


class MapId(QWidget):
    """
    A container class of widgets that represents user input for a map id. This class
    holds a Label and IDLineEdit.
    """

    def __init__(self):
        super(MapId, self).__init__()

        label = QLabel(self)
        label.setText("Map Id:")
        label.setToolTip("Beatmap id, not the mapset id!")
        self.field = IDLineEdit(self)

        layout = QGridLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(label, 0, 0, 1, 1)
        layout.addItem(spacer, 0, 1, 1, 1)
        layout.addWidget(self.field, 0, 2, 1, 3)
        self.setLayout(layout)


class UserId(QWidget):
    """
    A container class of widgets that represents user input for a user id. This class
    holds a Label and IDLineEdit.
    """

    def __init__(self):
        super(UserId, self).__init__()

        label = QLabel(self)
        label.setText("User Id:")
        label.setToolTip("User id, as seen in the profile url")
        self.field = IDLineEdit(self)

        layout = QGridLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(label, 0, 0, 1, 1)
        layout.addItem(spacer, 0, 1, 1, 1)
        layout.addWidget(self.field, 0, 2, 1, 3)
        self.setLayout(layout)


class CompareTop(QWidget):
    """
    A container class of widgets that represents user input for how many plays of a map to compare.
    This class holds a Label, Slider, and SpinBox.

    The SpinBox and Slider are linked internally by this class, so when one changes, so does the other.
    """

    def __init__(self):
        super(CompareTop, self).__init__()
        label = QLabel(self)
        label.setText("Compare Top:")
        label.setToolTip("Compare this many plays from the leaderboard")

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
        layout.addWidget(label, 0, 0, 1, 1)
        layout.addItem(spacer, 0, 1, 1, 1)
        layout.addWidget(slider, 0, 2, 1, 2)
        layout.addWidget(spinbox, 0, 4, 1, 1)
        self.setLayout(layout)

    # keep spinbox and slider in sync
    def update_spinbox(self, value):
        self.spinbox.setValue(value)

    def update_slider(self, value):
        self.slider.setValue(value)


class Threshold(QWidget):
    """
    A container class of widgets that represents user input for the threshold to consider a comparison a cheat.
    This class holds a Label, Slider, and SpinBox.

    The SpinBox and Slider are linked internally by this class, so when one changes, so does the other.
    """

    def __init__(self):
        super(Threshold, self).__init__()

        label = QLabel(self)
        label.setText("Threshold:")
        label.setToolTip("Cutoff for how similar two replays must be to be printed")
        self.label = label

        slider = QSlider(Qt.Horizontal)
        slider.setRange(0, 30)
        slider.setValue(THRESHOLD)
        slider.valueChanged.connect(self.update_spinbox)
        self.slider = slider

        spinbox = SpinBox(self)
        spinbox.setValue(THRESHOLD)
        spinbox.setAlignment(Qt.AlignCenter)
        spinbox.setRange(0, 30)
        spinbox.setSingleStep(1)
        spinbox.valueChanged.connect(self.update_slider)
        self.spinbox = spinbox

        layout = QGridLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(label, 0, 0, 1, 1)
        layout.addItem(spacer, 0, 1, 1, 1)
        layout.addWidget(slider, 0, 2, 1, 2)
        layout.addWidget(spinbox, 0, 4, 1, 1)
        self.setLayout(layout)

    # keep spinbox and slider in sync
    def update_spinbox(self, value):
        self.spinbox.setValue(value)

    def update_slider(self, value):
        self.slider.setValue(value)


class AutoThreshold(QWidget):
    def __init__(self):
        super(AutoThreshold, self).__init__()

        label = QLabel(self)
        label.setText("Auto Threshold:")
        label.setToolTip("Stddevs below average threshold to print for"+
                         "\n(typically between TLS and 2.5. The higher, the less results you will get)")
        self.label = label

        slider = QSlider(Qt.Horizontal)
        slider.setRange(10, 30)
        slider.setValue(20)
        slider.valueChanged.connect(self.update_spinbox)
        self.slider = slider

        spinbox = QDoubleSpinBox()
        spinbox.setValue(THRESHOLD)
        spinbox.setAlignment(Qt.AlignCenter)
        spinbox.setRange(1.0, 3.0)
        spinbox.setSingleStep(0.1)
        spinbox.setValue(2.0)
        spinbox.valueChanged.connect(self.update_slider)
        self.spinbox = spinbox

        layout = QGridLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(label, 0, 0, 1, 1)
        layout.addItem(spacer, 0, 1, 1, 1)
        layout.addWidget(slider, 0, 2, 1, 2)
        layout.addWidget(spinbox, 0, 4, 1, 1)
        self.setLayout(layout)

    # keep spinbox and slider in sync
    def update_spinbox(self, value):
        self.spinbox.setValue(value/10)

    def update_slider(self, value):
        self.slider.setValue(value*10)


class FolderChoose(QWidget):
    def __init__(self):
        super(FolderChoose, self).__init__()

        label = QLabel(self)
        label.setText("Choose Folder:")
        label.setToolTip("tmp")

        options = QFileDialog.Option()
        options |= QFileDialog.ShowDirsOnly
        options |= QFileDialog.HideNameFilterDetails
        self.file_chooser = QPushButton(self)
        self.file_chooser.setText("Choose Folder")
        self.file_chooser.pressed.connect(
            partial(QFileDialog.getExistingDirectory, caption="Select Output Folder", directory=QDir.currentPath(), options=options))

        layout = QGridLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(label, 0, 0, 1, 1)
        layout.addItem(spacer, 0, 1, 1, 3)
        layout.addWidget(self.file_chooser, 0, 4, 1, 1)
        self.setLayout(layout)
