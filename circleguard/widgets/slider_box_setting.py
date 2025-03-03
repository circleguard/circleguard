from PyQt6.QtWidgets import QFrame, QGridLayout, QLabel, QSpinBox
from PyQt6.QtCore import Qt
from settings import SingleLinkableSetting
from utils import spacer
from widgets.slider import Slider
from widgets.combiner import WidgetCombiner


class SliderBoxSetting(SingleLinkableSetting, QFrame):
    """
    A container class of a QLabel, QSlider, and SpinBox, and links the slider
    and spinbox to a setting (ie the default values of the slider and spinbox
    will be the value of the setting, and changes made to the slider or
    spinbox will affect the setting).
    """

    def __init__(self, parent, display, tooltip, setting, max_, min_=0):
        SingleLinkableSetting.__init__(self, setting)
        QFrame.__init__(self, parent)

        self.max_ = max_

        label = QLabel(self)
        label.setText(display)
        label.setToolTip(tooltip)
        self.label = label

        slider = Slider(Qt.Orientation.Horizontal)
        slider.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
        slider.setRange(min_, max_)
        # max value of max_, avoid errors when the setting is 2147483647 aka inf
        val = min(self.setting_value, max_)
        slider.setValue(val)
        self.slider = slider

        spinbox = self.spin_box()
        spinbox.setRange(min_, max_)
        spinbox.setSingleStep(1)
        spinbox.setFixedWidth(120)
        spinbox.setValue(self.setting_value)
        spinbox.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.spinbox = spinbox
        self.combined = WidgetCombiner(slider, spinbox, self)

        self.slider.valueChanged.connect(
            lambda val: self.on_setting_changed_from_gui(val, set_spinbox=True)
        )
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
