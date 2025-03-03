from PyQt6.QtWidgets import QFrame, QLabel, QHBoxLayout
from PyQt6.QtGui import QIcon
from settings import SingleLinkableSetting
from utils import resource_path
from widgets.push_button import PushButton
from widgets.whats_this import WhatsThis
from widgets.file_chooser_button import FileChooserButton

class FileChooserSetting(SingleLinkableSetting, QFrame):
    def __init__(
        self,
        label_text,
        button_text,
        tooltip,
        file_chooser_type,
        setting,
        name_filters=None,
    ):
        SingleLinkableSetting.__init__(self, setting)
        QFrame.__init__(self)

        self.whats_this = WhatsThis(
            "A plaintext (.txt) file, containing a user id (NOT a username) "
            "on each line. If given, users listed in\nthis file will not show up in your investigation "
            "results, even if their replay is under a set threshold.\n\n"
            "You can leave comments on any line of the file with a pound sign (#) followed by "
            "your comment.\nNo other text is allowed besides comments and user ids."
        )
        self.whats_this.setFixedWidth(20)

        self.setting_label = QLabel(label_text)

        self.path_label = QLabel(self.setting_value)
        self.path_label.setWordWrap(True)

        self.file_chooser = FileChooserButton(
            button_text, file_chooser_type, name_filters
        )
        self.file_chooser.path_chosen_signal.connect(self._on_setting_changed_from_gui)
        self.file_chooser.setFixedWidth(90)

        self.delete_button = PushButton(self)
        self.delete_button.setIcon(QIcon(resource_path("delete.png")))
        self.delete_button.setToolTip("clear whitelist file path")
        self.delete_button.clicked.connect(self.reset_path)
        self.delete_button.setFixedWidth(25)

        self.layout = QHBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.addWidget(self.whats_this)
        self.layout.addWidget(self.setting_label)
        self.layout.addWidget(self.path_label)
        self.layout.addWidget(self.file_chooser)
        self.layout.addWidget(self.delete_button)
        self.setLayout(self.layout)

    def _on_setting_changed_from_gui(self, new_value):
        # FileChooserButton gives us a Path, we want our setting to be a str
        self.on_setting_changed_from_gui(str(new_value))

    def on_setting_changed(self, setting, new_value):
        self.path_label.setText(new_value)

    def reset_path(self):
        self.on_setting_changed_from_gui("")
