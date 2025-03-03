import sys
from pathlib import Path
import urllib
from PyQt6.QtWidgets import (
    QFrame,
    QVBoxLayout,
    QListWidget,
    QListWidgetItem,
    QApplication,
)
from PyQt6.QtGui import QShortcut
from PyQt6.QtCore import Qt, QSize, QTimer
from widgets.selectable_loadable import SelectableLoadable


class LoadableCreation(QFrame):
    LOADABLE_SIZE = QSize(450, 150)

    def __init__(self):
        super().__init__()
        self.loadables = []
        self.previous_combobox_state = None
        self.setAcceptDrops(True)

        self.list_widget = QListWidget()
        self.list_widget.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.list_widget.setViewMode(QListWidget.ViewMode.IconMode)
        self.list_widget.setGridSize(self.LOADABLE_SIZE)
        # apparently list widgets allow you to move widgets around? We don't
        # want to allow that though.
        self.list_widget.setMovement(QListWidget.Movement.Static)

        self.cg_loadables_to_selectable_loadables = {}

        QShortcut(Qt.Key.Key_R, self, lambda: self.select_loadable("Map Replay"))
        QShortcut(Qt.Key.Key_L, self, lambda: self.select_loadable("Local Replay"))
        QShortcut(Qt.Key.Key_M, self, lambda: self.select_loadable("Map"))
        QShortcut(Qt.Key.Key_U, self, lambda: self.select_loadable("User"))
        QShortcut(
            Qt.Key.Key_A, self, lambda: self.select_loadable("All User Replays on Map")
        )

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        layout.addWidget(self.list_widget)
        self.setLayout(layout)

        # prepopulate with a single loadable
        self.new_loadable()

    def reset_active_window(self):
        # See the caller of this method for reasoning as to why this method
        # exists.
        # imported locally here to avoid circular imports
        from gui.circleguard_window import CircleguardWindow

        QApplication.setActiveWindow(CircleguardWindow.INSTANCE)

    def loadable_input_changed(self, loadable):
        # only allow the bottommost loadable to create new ones
        if loadable != self.most_recent_loadable:
            return
        self.new_loadable()

    def resizeEvent(self, event):
        ret = super().resizeEvent(event)
        # I don't totally understand how, but the positions of the loadables in
        # the list widget can get into a bad state when the window is resized.
        # A recalculation of the layout seems to fix this, so force recalc on
        # every resize event.
        self.list_widget.scheduleDelayedItemsLayout()
        return ret

    def select_loadable(self, type_):
        self.most_recent_loadable.select_loadable(type_)
        self.new_loadable()

    def new_loadable(self):
        loadable = SelectableLoadable()
        self.cg_loadables_to_selectable_loadables[loadable] = None
        loadable.should_show_sim_combobox = (
            self.previous_combobox_state == Qt.CheckState.Checked.value
        )
        # some loadables have input widgets which can become arbitrarily long,
        # for instance ReplayPathLoadable's ReplayChooser which displays the
        # chosen file's location. This would cause the loadable to increase in
        # size in the list widget, which looks terrible as the list widget
        # expects uniform size.
        # Long story short enforce constant size on loadables no matter what.
        loadable.setFixedSize(self.LOADABLE_SIZE)

        loadable.deleted_pressed.connect(lambda: self.remove_loadable(loadable))
        loadable.input_changed.connect(lambda: self.loadable_input_changed(loadable))
        loadable.disable_button_shift_clicked.connect(
            lambda: self.disable_button_shift_clicked(loadable)
        )
        # don't allow the bottommost loadable (which this new one will soon
        # become) to be deleted, users could accidentally remove all loadables
        loadable.hide_delete()

        self.most_recent_loadable = loadable
        self.loadables.append(loadable)
        # show the delete button on the second to last handler, if it exists,
        # since it can now be deleted as it isn't the final loadable
        if len(self.loadables) > 1:
            self.loadables[-2].show_delete()

        # god bless this SO answer https://stackoverflow.com/a/49272941/12164878
        # I would never have thought to set the size hint manually otherwise
        # (and doing so is very much necessary).
        item = QListWidgetItem(self.list_widget)
        self.list_widget.addItem(item)
        item.setSizeHint(self.LOADABLE_SIZE)
        # list items get an annoying highlight in the middle of the widget if
        # we don't disable interaction.
        item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEnabled)
        self.list_widget.setItemWidget(item, loadable)
        # without this call, list items will be added in the wrong spot
        # and will only correct themselves once the window is resized or another
        # loadable is added. I'm probably doing something wrong that's the
        # root cause of this behavior, but I can't figure out what and this call
        # fixes it.
        # https://stackoverflow.com/a/48773670/12164878
        self.list_widget.scheduleDelayedItemsLayout()

        # This is a weird one. Adding our ``SelectableLoadable`` to the list
        # widget causes our main window (``CircleguardWindow``) to not be the
        # active window anymore, which means any mouse clicks onto widgets that
        # want to receive focus (like LineEdits) will not recieve focus until
        # the window becomes the main window again. So we have to force the
        # CircleguardWindow to be the main window.
        # However, if we do so directly here, the cg window will still not be
        # the main window afterwards. I believe this is because the list widget
        # is scheduling some events to be fired shortly afterwards that is
        # causing the active window removal, so we need to wait for those to
        # occurr before we can do anything. Even 10ms seemed to work, but I'm
        # going for 100 to be safe.
        timer = QTimer(self)
        timer.setSingleShot(True)
        timer.timeout.connect(self.reset_active_window)
        timer.start(100)

    def remove_loadable(self, loadable):
        # since we're dealing with a QListWidget, we can't just hide the
        # loadable widget - we need to remove it from the list widget entirely.
        # In typical qt fashion, the only way to do so is with an index into the
        # list widget.
        index = self.loadables.index(loadable)
        self.loadables.remove(loadable)
        self.list_widget.takeItem(index)
        if loadable == self.most_recent_loadable:
            self.most_recent_loadable = self.loadables[-1]

        # necessary to reclaim this memory when we delete the associated
        # loadable
        self.cg_loadables_to_selectable_loadables[loadable] = None

    def disable_button_shift_clicked(self, caller_loadable):
        # a shift click on a loadable that is enabled means we want to disable
        # every *other* loadable.
        if caller_loadable.enabled:
            for loadable in self.loadables:
                if loadable != caller_loadable:
                    loadable.disable()
        # but a shift click on a disabled loadable means we want to enable *all*
        # loadables.
        else:
            for loadable in self.loadables:
                loadable.enable()

    def cg_loadables(self):
        """
        Returns the loadables in this widget as (potentially) unloaded
        circleguard loadables.
        """
        loadables = []
        for loadable in self.loadables:
            # loadables can be selectively enabled or disabled
            if not loadable.enabled:
                continue
            previous = self.cg_loadables_to_selectable_loadables[loadable]
            cg_loadable = loadable.cg_loadable(previous)
            self.cg_loadables_to_selectable_loadables[loadable] = cg_loadable
            # can't do ``not cg_loadable`` because for ReplayContainers they
            # may not be loaded yet and so have length 0 and are thus falsey,
            # but we still want to return them
            if cg_loadable is None:
                continue
            loadables.append(cg_loadable)
        return loadables

    def check_and_mark_required_fields(self):
        all_valid = True
        for loadable in self.loadables:
            # only check enabled loadables, disabled + empty loadables should
            # not stop the run from succeeding
            if loadable.enabled and not loadable.check_and_mark_required_fields():
                all_valid = False
        return all_valid

    def similarity_cb_state_changed(self, state):
        self.previous_combobox_state = state
        for loadable in self.loadables:
            if state == Qt.CheckState.Unchecked.value:
                loadable.hide_sim_combobox()
            else:
                loadable.show_sim_combobox()
            loadable.should_show_sim_combobox = state == Qt.CheckState.Checked.value

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
        paths = []

        # TODO abstract osr drag-and-drop file handling, the code below
        # is duplicated in ReplayDropArea below
        for path in paths_unprocessed.split("\n"):
            if sys.platform != "win32":
                path = "/" + path
            path = urllib.parse.unquote(path)
            path = Path(path)
            if not (path.suffix == ".osr" or path.is_dir()):
                continue

            paths.append(path)

        # if none of the files were replays (or a folder), don't accept the drop
        # event
        if not paths:
            return

        event.acceptProposedAction()

        for path in paths:
            self.most_recent_loadable.select_loadable("Local Replay")
            # `loadable` will be an instance of `ReplayPathLoadable`
            loadable = self.most_recent_loadable.stacked_layout.currentWidget()
            loadable.path_input.set_path(path)
            self.new_loadable()
