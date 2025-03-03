from PyQt6.QtWidgets import QFrame, QGridLayout, QLabel, QSpacerItem, QSizePolicy
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import Qt, pyqtSignal
from utils import resource_path
from widgets.push_button import PushButton


class RunWidget(QFrame):
    """
    A single run with QLabel displaying a state (either queued, finished,
    loading replays, comparing, or canceled), and a cancel QPushButton
    if not already finished or canceled.
    """

    widget_deleted = pyqtSignal(int)

    def __init__(self, run):
        super().__init__()

        self.run_id = run.run_id

        self.status = "Queued"
        self.label = QLabel(self)
        self.text = f"[Run {self.run_id + 1}] Run with {len(run.loadables)} Loadables"
        self.label.setText(self.text)

        self.status_label = QLabel(self)
        self.status_label.setText("<b>Status: " + self.status + "</b>")
        self.status_label.setTextFormat(Qt.TextFormat.RichText)  # so we can bold it
        self.cancel_button = PushButton(self)
        self.cancel_button.setText("Cancel")
        self.cancel_button.setFixedWidth(125)
        self.label.setFixedHeight(int(self.cancel_button.size().height() * 0.75))

        self.up_button = PushButton(self)
        self.up_button.setIcon(QIcon(resource_path("up_arrow.svg")))
        self.up_button.setFixedWidth(30)
        self.down_button = PushButton(self)
        self.down_button.setIcon(QIcon(resource_path("down_arrow.svg")))
        self.down_button.setFixedWidth(30)

        # if we hide the up or down buttons of this run, we don't want to have
        # that change the spacing of the other widgets to keep things lined up.
        for button in [self.up_button, self.down_button]:
            size_policy = button.sizePolicy()
            size_policy.setRetainSizeWhenHidden(True)
            button.setSizePolicy(size_policy)

        self.layout = QGridLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.addWidget(self.label, 0, 0, 1, 1)
        self.layout.addWidget(self.status_label, 0, 1, 1, 1)
        # needs to be redefined because RunWidget is being called from a
        # different thread or something? get weird errors when not redefined
        SPACER = QSpacerItem(
            100, 0, QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Minimum
        )
        self.layout.addItem(SPACER, 0, 2, 1, 1)
        self.layout.addWidget(self.cancel_button, 0, 3, 1, 1)
        self.layout.addWidget(self.up_button, 0, 4, 1, 1)
        self.layout.addWidget(self.down_button, 0, 5, 1, 1)
        self.setLayout(self.layout)

    def update_status(self, status):
        if status == "Finished":
            self.widget_deleted.emit(self.run_id)
            self.deleteLater()
            return

        self.status = status
        self.status_label.setText("<b>Status: " + self.status + "</b>")

    def cancel(self):
        self.widget_deleted.emit(self.run_id)
        self.deleteLater()
