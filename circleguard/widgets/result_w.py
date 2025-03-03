from PyQt6.QtWidgets import QFrame, QGridLayout, QLabel, QComboBox
from PyQt6.QtGui import QCursor
from PyQt6.QtCore import Qt, pyqtSignal
from utils import AnalysisResult, spacer
from widgets.combo_box import ComboBox
from widgets.push_button import PushButton
from widgets.frametime_window import FrametimeWindow
from widgets.replay_data_window import ReplayDataWindow


class ResultW(QFrame):
    """
    Stores the result of a comparison that can be replayed at any time.
    Contains a QLabel, QPushButton (visualize) and QPushButton (copy to clipboard).
    """

    template_button_pressed_signal = pyqtSignal()
    visualize_button_pressed_signal = pyqtSignal()

    def __init__(self, text, result, replays):
        super().__init__()
        self.result = result
        self.replays = replays

        self.label = QLabel(self)
        self.label.setText(text)
        self.label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.label.setCursor(QCursor(Qt.CursorShape.IBeamCursor))
        self.label.setTextFormat(Qt.TextFormat.RichText)
        self.label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextBrowserInteraction
        )
        self.label.setOpenExternalLinks(True)

        self.visualize_button = PushButton(self)
        self.visualize_button.setText("Visualize")
        self.visualize_button.clicked.connect(self.visualize_button_pressed_signal.emit)
        self.visualize_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        if len(replays) == 1:
            self.set_layout_single()
        # at the moment, this only happens for replay stealing and when
        # visualizing multiple replays
        else:
            self.set_layout_multiple()

    def set_layout_single(self):
        self.actions_combobox = ComboBox()
        self.actions_combobox.addItem("More")
        self.actions_combobox.addItem("View Frametimes", "View Frametimes")
        self.actions_combobox.addItem("View Replay Data", "View Replay Data")
        self.actions_combobox.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.actions_combobox.activated.connect(self.action_combobox_activated)

        layout = QGridLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.label, 0, 0, 1, 4)
        layout.addItem(spacer(), 0, 4, 1, 1)
        if isinstance(self.result, AnalysisResult):
            layout.addWidget(self.visualize_button, 0, 5, 1, 3)
            layout.addWidget(self.actions_combobox, 0, 8, 1, 1)
        else:
            template_button = self.new_template_button()

            layout.addWidget(self.visualize_button, 0, 5, 1, 2)
            layout.addWidget(template_button, 0, 7, 1, 1)
            layout.addWidget(self.actions_combobox, 0, 8, 1, 1)

        self.setLayout(layout)

    def set_layout_multiple(self):
        layout = QGridLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.label, 0, 0, 1, 1)
        layout.addItem(spacer(), 0, 1, 1, 1)
        if isinstance(self.result, AnalysisResult):
            layout.addWidget(self.visualize_button, 0, 2, 1, 2)
        else:
            template_button = self.new_template_button()
            layout.addWidget(self.visualize_button, 0, 2, 1, 1)
            layout.addWidget(template_button, 0, 3, 1, 1)

        self.setLayout(layout)

    def action_combobox_activated(self):
        if self.actions_combobox.currentData() == "View Frametimes":
            self.frametime_window = FrametimeWindow(self.replays[0])
            self.frametime_window.show()
        if self.actions_combobox.currentData() == "View Replay Data":
            self.replay_data_window = ReplayDataWindow(self.replays[0])
            self.replay_data_window.show()
        self.actions_combobox.setCurrentIndex(0)

    def new_template_button(self):
        template_button = PushButton(self)
        template_button.setText("Copy Template")
        template_button.setFixedWidth(120)
        template_button.clicked.connect(self.template_button_pressed_signal.emit)
        return template_button
