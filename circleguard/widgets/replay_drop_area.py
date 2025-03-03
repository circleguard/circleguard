import sys
from pathlib import Path
from functools import partial
import urllib
from PyQt6.QtWidgets import QFrame, QGridLayout, QLabel, QGraphicsOpacityEffect
from PyQt6.QtGui import QPainter, QPen
from PyQt6.QtCore import Qt
from utils import ACCENT_COLOR
from widgets.path import PathWidget


# provided for our Analysis window. There's probably some shared code that
# we could abstract out from this and `DropArea`, but it's not worth it atm
class ReplayDropArea(QFrame):
    def __init__(self):
        super().__init__()
        self.path_widgets = []

        self.setAcceptDrops(True)

        self.info_label = QLabel("drag and drop .osr files here")
        font = self.info_label.font()
        font.setPointSize(20)
        self.info_label.setFont(font)
        self.info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # https://stackoverflow.com/a/59022793/12164878
        effect = QGraphicsOpacityEffect(self)
        effect.setOpacity(0.5)
        self.info_label.setGraphicsEffect(effect)
        self.info_label.setAutoFillBackground(True)

        layout = QGridLayout()
        layout.setContentsMargins(25, 25, 10, 10)
        layout.addWidget(self.info_label)
        self.setLayout(layout)

    def dragEnterEvent(self, event):
        event.acceptProposedAction()

    def dropEvent(self, event):
        mimedata = event.mimeData()
        # users can drop multiple files, in which case we need to consider each
        # separately
        paths_unprocessed = (
            mimedata.data("text/uri-list")
            .data()
            .decode("utf-8")
            .rstrip()
            .replace("file:///", "")
            .replace("\r", "")
        )
        path_widgets = []

        for path in paths_unprocessed.split("\n"):
            # I might be misunderstanding mime URIs, but it seems to me that
            # files are always prepended with `file:///` on all platforms, but
            # on macOS and Linux the leading slash is not included (there are
            # only three slashes, not four), which confuses pathlib as it will
            # interpret the path as relative and not absolute. To fix this we
            # prepend a slash on macOS and Linux, but not windows, as their
            # denotation for a root dir is different (they use `C:`).
            if sys.platform != "win32":
                path = "/" + path
            # if the file path has a space (or I believe any character which
            # requires an encoding), qt will give it to us in its encoded form.
            # Pathlib doesn't like this, so we need to unencode (unquote) it.
            path = urllib.parse.unquote(path)
            path = Path(path)
            if not (path.suffix == ".osr" or path.is_dir()):
                continue

            to_add = []
            if path.is_dir():
                for replay_path in path.glob("*.osr"):
                    path_widget = PathWidget(replay_path)
                    to_add.append(path_widget)
            else:
                path_widget = PathWidget(path)
                to_add.append(path_widget)

            for path_widget in to_add:
                # don't let users drop the same file twice
                if path_widget in self.path_widgets:
                    continue
                path_widgets.append(path_widget)

        # if none of the files were replays, don't accept the drop event
        if not path_widgets:
            return

        event.acceptProposedAction()
        # hide the info label and fill top down now that we have things to show
        self.info_label.hide()
        self.layout().setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop
        )

        for path_widget in path_widgets:
            # `lambda` is late binding so we can't use it here or else all the
            # delete buttons will delete the last widget of the list.
            # workaround: use `partial` instead of `lambda`.
            # https://docs.python-guide.org/writing/gotchas/#late-binding-closures
            path_widget.delete_button.clicked.connect(
                partial(self.delete_path_widget, path_widget)
            )
            self.layout().addWidget(path_widget)

        self.path_widgets.extend(path_widgets)

    def delete_path_widget(self, path_widget):
        path_widget.hide()
        self.path_widgets.remove(path_widget)

        # re-show the info label if the user deletes all their replays
        if len(self.path_widgets) == 0:
            self.layout().setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.info_label.show()

    def all_loadables(self, flush):
        # if ``flush`` is true, flush our cache in a hacky way by setting the
        # backing attribute to null so the next time it's accessed it's
        # recreated.
        for path_widget in self.path_widgets:
            if flush:
                path_widget._cg_loadable = None
        return [path_widget.cg_loadable for path_widget in self.path_widgets]

    def paintEvent(self, event):
        super().paintEvent(event)
        pen = QPen()
        pen.setColor(ACCENT_COLOR)
        pen.setWidth(3)
        # 4 (pen width units of) accent color, followed by 4 (pen width units
        # of) nothing, then repeat
        pen.setDashPattern([4, 4])
        painter = QPainter(self)
        painter.setPen(pen)
        painter.drawRoundedRect(0, 5, self.width() - 5, self.height() - 7, 3, 3)
