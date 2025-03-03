from PyQt6.QtWidgets import QFrame, QHBoxLayout
from PyQt6.QtCore import Qt
from widgets.labeled_checkbox import LabeledCheckbox

class InvestigationCheckboxes(QFrame):
    def __init__(self):
        super().__init__()

        self.similarity_cb = LabeledCheckbox("Similarity")
        self.ur_cb = LabeledCheckbox("Unstable Rate")
        self.frametime_cb = LabeledCheckbox("Frametime")
        self.snaps_cb = LabeledCheckbox("Snaps")
        self.manual_analysis_cb = LabeledCheckbox("Manual Analysis")

        layout = QHBoxLayout()
        layout.setSpacing(25)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(self.similarity_cb)
        layout.addWidget(self.ur_cb)
        layout.addWidget(self.frametime_cb)
        layout.addWidget(self.snaps_cb)
        layout.addWidget(self.manual_analysis_cb)
        self.setLayout(layout)

    def enabled_investigations(self):
        enabled_investigations = []
        if self.similarity_cb.checkbox.isChecked():
            enabled_investigations.append("Similarity")
        if self.ur_cb.checkbox.isChecked():
            enabled_investigations.append("Unstable Rate")
        if self.frametime_cb.checkbox.isChecked():
            enabled_investigations.append("Frametime")
        if self.snaps_cb.checkbox.isChecked():
            enabled_investigations.append("Snaps")
        if self.manual_analysis_cb.checkbox.isChecked():
            enabled_investigations.append("Manual Analysis")
        return enabled_investigations
