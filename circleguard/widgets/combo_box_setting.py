from PyQt6.QtWidgets import QFrame, QGridLayout, QLabel, QComboBox
from PyQt6.QtCore import Qt
from settings import LinkableSetting
from utils import spacer
from widgets.combo_box import ComboBox


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
        combobox.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
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
        layout.addWidget(combobox, 0, 2, 1, 3, Qt.AlignmentFlag.AlignRight)
        self.setLayout(layout)

    def selection_changed(self):
        self.on_setting_changed_from_gui(self.setting, self.combobox.currentData())
