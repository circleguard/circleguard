from PyQt6.QtWidgets import QFrame, QGridLayout


class WidgetCombiner(QFrame):
    def __init__(self, widget1, widget2, parent):
        super().__init__(parent)
        # these widgets get created outside of WidgetCombiner and might
        # have had a different parent - but they're our children now!
        widget1.setParent(self)
        widget2.setParent(self)
        self.layout = QGridLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.addWidget(widget1, 0, 0, 1, 1)
        self.layout.addWidget(widget2, 0, 1, 1, 1)
        self.setLayout(self.layout)
