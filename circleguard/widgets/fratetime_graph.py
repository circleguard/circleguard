from PyQt6.QtWidgets import QFrame, QVBoxLayout
from settings import get_setting


class FrametimeGraph(QFrame):
    def __init__(self, replay):
        super().__init__()
        from circleguard import KeylessCircleguard
        from matplotlib.backends.backend_qt5agg import FigureCanvas  # pylint: disable=no-name-in-module
        from matplotlib.figure import Figure

        figure = Figure(figsize=(5, 5))
        cg = KeylessCircleguard()
        show_cv = get_setting("frametime_graph_display") == "cv"
        figure = cg.frametime_graph(replay, cv=show_cv, figure=figure)

        self.canvas = FigureCanvas(figure)

        layout = QVBoxLayout()
        layout.addWidget(self.canvas)
        self.setLayout(layout)
