from PyQt6.QtWidgets import QLabel, QToolTip
from PyQt6.QtGui import QPixmap
from utils import resource_path


class WhatsThis(QLabel):
    """
    Uses a label as a carrier for displaying a question mark image, which
    displays a tooltip on hover immediately, with no delay. This is useful for
    confusing aspects of circleguard which need explicit clarification beyond a
    normal delayed tooltip on hover.
    """

    def __init__(self, text):
        super().__init__()

        self.text = text
        pixmap = QPixmap(resource_path("question_mark.png"))
        self.setPixmap(pixmap)

    def enterEvent(self, event):
        global_pos = self.mapToGlobal(event.position()).toPoint()
        QToolTip.showText(global_pos, self.text)
