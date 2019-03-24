from PyQt5.QtWidgets import *
from circleguard import __version__
# Pycharm doesn't (and probably other IDEs too) like this code so ignore the errors lel


class Window(QWidget):
    def __init__(self):
        super().__init__()
        self.state = QComboBox()
        self.modes = [
            'Screen User',
            'Check Map',
            'Check User on Map',
            'Check Local Replays'
        ]

        self.state.addItems(self.modes)
        self.state.activated.connect(self.circleguard_print_mode)
        self.state.setToolTip('Choose the mode to run Circleguard in')

        self.left = QPushButton('print version')
        self.left.clicked.connect(self.circleguard_print_version)
        self.left.setToolTip('This will print the version of circleguard')

        self.right = QPushButton('run')
        self.right.clicked.connect(self.circleguard_run)
        self.right.setToolTip('This will run circleguard with the selected settings')

        self.user_id_label = QLabel(self)
        self.user_id_label.setText('User Id:')
        self.user_id_label.setToolTip('This can be found in the profile url and only consists of numbers')
        self.user_id_line = QLineEdit(self)
        self.user_id_line.setToolTip('This can be found in the profile url and only consists of numbers')

        self.map_id_label = QLabel(self)
        self.map_id_label.setText('Map Id:')
        self.map_id_label.setToolTip('This is the beatmap id, not the beatmapset id!')
        self.map_id_line = QLineEdit(self)
        self.map_id_line.setToolTip('This is the beatmap id, not the beatmapset id!')

        self.grid = QGridLayout()
        self.grid.addWidget(self.state, 1, 1, 1, 4)
        self.grid.addWidget(self.user_id_label, 2, 1, 2, 1)
        self.grid.addWidget(self.user_id_line, 2, 2, 2, 3)
        self.grid.addWidget(self.map_id_label, 4, 1, 4, 1)
        self.grid.addWidget(self.map_id_line, 4, 2, 4, 3)

        self.setLayout(self.grid)
        self.setWindowTitle(f'Circleguard gui !!WIP!! (backend version {__version__})')

        # final setup
        self.circleguard_print_mode(0)

        return

    def circleguard_print_version(self):
        print(f'Using Version {__version__} from circleguard ')
        return

    def circleguard_run(self):
        print(f'You are a cheater, Harry!')
        return

    def circleguard_print_mode(self, i):
        print(f'current mode is {i}. This corresponds to {self.modes[i]}')
        # user, map
        modes = [(True, False), (False, True), (True, True), (False, False)]
        self.user_id_line.setEnabled(modes[i][0])
        self.user_id_label.setEnabled(modes[i][0])
        self.map_id_line.setEnabled(modes[i][1])
        self.map_id_label.setEnabled(modes[i][1])
        return


if __name__ == '__main__':
    app = QApplication([])
    app.setStyle('Fusion')
    test_window = Window()
    test_window.show()
    app.exec_()
