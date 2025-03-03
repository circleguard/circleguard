from PyQt6.QtWidgets import QFrame, QGridLayout, QLabel, QFileDialog
from widgets.file_chooser_button import FileChooserButton

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
        self.file_chooser = FileChooserButton(
            "Choose replay",
            QFileDialog.FileMode.ExistingFile,
            ["osu! Replay File (*.osr)"],
        )
        self.folder_chooser = FileChooserButton(
            "Choose folder", QFileDialog.FileMode.Directory
        )

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

    # exposed for external usage, identical to `handle_new_path` except always
    # sets `selection_made` to `True`
    def set_path(self, path):
        self.path = path
        self.path_label.setText(str(path))
        self.selection_made = True

    def handle_new_path(self, path):
        self.path = path
        self.path_label.setText(str(path))
        self.selection_made = (
            self.file_chooser.selection_made or self.folder_chooser.selection_made
        )

    def show_required(self):
        self.setStyleSheet(
            "ReplayChooser { border: 1px solid red; border-radius: 4px; padding: 2px }"
        )

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        self.reset_required()

    def reset_required(self):
        self.setStyleSheet(self.old_stylesheet)
