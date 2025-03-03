from pathlib import Path
from PyQt6.QtWidgets import QFileDialog
from PyQt6.QtCore import pyqtSignal
from widgets.push_button import PushButton


class FileChooserButton(PushButton):
    path_chosen_signal = pyqtSignal(Path)  # emits the selected path

    def __init__(self, text, file_mode=QFileDialog.FileMode.AnyFile, name_filters=None):
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
