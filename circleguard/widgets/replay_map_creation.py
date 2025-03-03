from PyQt6.QtWidgets import QFrame, QLabel, QVBoxLayout, QGraphicsOpacityEffect
from PyQt6.QtCore import Qt
from widgets.replay_map_vis import ReplayMapVis


class ReplayMapCreation(QFrame):
    def __init__(self):
        super().__init__()
        self.loadables = []

        label = QLabel("Enter online replays here")
        font = label.font()
        font.setPointSize(17)
        label.setFont(font)
        effect = QGraphicsOpacityEffect(self)
        effect.setOpacity(0.8)
        label.setGraphicsEffect(effect)
        label.setAutoFillBackground(True)

        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        layout.addWidget(label)
        self.setLayout(layout)

        # prepopulate with a single loadable
        self.new_loadable()

    def loadable_input_changed(self, loadable):
        # only allow the bottommost loadable to create new ones
        if loadable != self.most_recent_loadable:
            return
        self.new_loadable()

    def new_loadable(self):
        loadable = ReplayMapVis()
        loadable.delete_button.clicked.connect(lambda: self.remove_loadable(loadable))
        loadable.input_changed.connect(lambda: self.loadable_input_changed(loadable))
        # don't allow the bottommost loadable (which this new one will soon
        # become) to be deleted, users could accidentally remove all loadables
        loadable.hide_delete()

        self.most_recent_loadable = loadable
        self.loadables.append(loadable)
        # show the delete button on the second to last handler, if it exists,
        # since it can now be deleted as it isn't the final loadable
        if len(self.loadables) > 1:
            self.loadables[-2].show_delete()

        self.layout().addWidget(loadable)

    def remove_loadable(self, loadable):
        loadable.hide()
        self.loadables.remove(loadable)
        if loadable == self.most_recent_loadable:
            self.most_recent_loadable = self.loadables[-1]

    def all_loadables(self):
        """
        Returns the loadables in this widget as unloaded circleguard loadables.
        """
        loadables = []
        for loadable in self.loadables:
            cg_loadable = loadable.cg_loadable()
            if not cg_loadable:
                continue
            loadables.append(cg_loadable)
        return loadables
