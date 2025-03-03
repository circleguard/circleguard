from PyQt6.QtWidgets import QFrame

class QVLine(QFrame):
    def __init__(self, shadow=QFrame.Shadow.Plain):
        super().__init__()
        self.setFrameShape(QFrame.Shape.VLine)
        self.setFrameShadow(shadow)
