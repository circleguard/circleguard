from PyQt6.QtWidgets import QFrame, QGridLayout, QLabel
from utils import spacer

from widgets.line_edit import LineEdit
from widgets.password_edit import PasswordEdit
from widgets.id_line_edit import IDLineEdit

class InputWidget(QFrame):
    """
    A container class of widgets that represents user input for an id. This class
    holds a Label and either a PasswordEdit, IDLineEdit, or LineEdit, depending
    on the constructor call. The former two inherit from LineEdit.
    """

    def __init__(self, title, tooltip, type_):
        super().__init__()

        label = QLabel(self)
        label.setText(title + ":")
        label.setToolTip(tooltip)
        if type_ == "password":
            self.field = PasswordEdit(self)
        if type_ == "id":
            self.field = IDLineEdit(self)
        if type_ == "normal":
            self.field = LineEdit(self)

        self.layout = QGridLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.addWidget(label, 0, 0, 1, 1)
        self.layout.addItem(spacer(), 0, 1, 1, 1)
        self.layout.addWidget(self.field, 0, 2, 1, 3)
        self.setLayout(self.layout)

    def show_required(self):
        """
        Shows a red border around the LineEdit to indicate a field that must be
        filled in. This border is removed when the LineEdit receieves focus again.
        """
        self.field.show_required()

    def value(self):
        """
        Retrieves the string value of the field in this input widget.
        """
        return self.field.text()
