from PyQt6.QtWidgets import QFrame


class QHLine(QFrame):
    def __init__(self, shadow=QFrame.Shadow.Plain):
        super().__init__()
        self.setFrameShape(QFrame.Shape.HLine)
        self.setFrameShadow(shadow)
