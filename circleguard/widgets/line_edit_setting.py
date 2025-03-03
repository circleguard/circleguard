from PyQt6.QtWidgets import QFrame, QHBoxLayout
from settings import SingleLinkableSetting
from widgets.input import InputWidget


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
        self.layout = QHBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.addWidget(self.input_)
        self.setLayout(self.layout)

    def on_setting_changed(self, setting, new_value):
        self.input_.field.setText(new_value)
