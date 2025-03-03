from PyQt6.QtWidgets import QSlider, QStyle
from PyQt6.QtGui import QCursor
from PyQt6.QtCore import Qt


# A slider which moves directly to the clicked position when clicked
# Implementation from https://stackoverflow.com/a/29639127/12164878
class Slider(QSlider):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

    def mousePressEvent(self, event):
        self.setValue(
            QStyle.sliderValueFromPosition(
                self.minimum(),
                self.maximum(),
                event.position().toPoint().x(),
                self.width(),
            )
        )

    def mouseMoveEvent(self, event):
        self.setValue(
            QStyle.sliderValueFromPosition(
                self.minimum(),
                self.maximum(),
                event.position().toPoint().x(),
                self.width(),
            )
        )
