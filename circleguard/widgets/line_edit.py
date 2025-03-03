from PyQt6.QtWidgets import QLineEdit

from settings import get_setting

# TODO cmd + z doesn't undo operations here, figure out why
class LineEdit(QLineEdit):
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
