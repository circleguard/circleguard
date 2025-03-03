from PyQt6.QtWidgets import (
    QFrame,
    QVBoxLayout,
    QTableWidget,
    QTableWidgetItem,
    QAbstractItemView,
)


class ReplayDataTable(QFrame):
    def __init__(self, replay):
        super().__init__()
        from circleguard import Key

        table = QTableWidget()
        table.setColumnCount(4)
        table.setRowCount(len(replay.t))
        table.setHorizontalHeaderLabels(["Time (ms)", "x", "y", "keys pressed"])
        # https://forum.qt.io/topic/82749/how-to-make-qtablewidget-read-only
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)

        for i, data in enumerate(zip(replay.t, replay.xy, replay.k)):
            t, xy, k = data
            if i == 0:
                text = str(t)
            else:
                t_prev = replay.t[i - 1]
                text = f"{t} ({t - t_prev})"

            item = QTableWidgetItem(text)
            table.setItem(i, 0, item)

            item = QTableWidgetItem(str(xy[0]))
            table.setItem(i, 1, item)

            item = QTableWidgetItem(str(xy[1]))
            table.setItem(i, 2, item)

            ks = []
            if Key.K1 & k:
                ks.append("K1")
            # M1 is always set if K1 is set, so only append if it's set without
            # K1. Same with M2/K2
            elif Key.M1 & k:
                ks.append("M1")
            if Key.K2 & k:
                ks.append("K2")
            elif Key.M2 & k:
                ks.append("M2")
            item = QTableWidgetItem(" + ".join(ks))
            table.setItem(i, 3, item)

        layout = QVBoxLayout()
        layout.addWidget(table)
        self.setLayout(layout)
