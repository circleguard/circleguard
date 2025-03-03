from PyQt6.QtWidgets import QFrame, QGridLayout, QLabel
from PyQt6.QtCore import Qt
from settings import SingleLinkableSetting
from widgets.check_box import CheckBox
from widgets.centered import CenteredWidget


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
        self.layout.addWidget(item, 0, 1, 1, 1, Qt.AlignmentFlag.AlignRight)
        self.setLayout(self.layout)

    def on_setting_changed(self, setting, new_value):
        self.box.setChecked(new_value)
