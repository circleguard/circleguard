from PyQt5.QtWidgets import *
from circleguard import __version__
# Pycharm doesn't (and probably other IDEs too) like this code so ignore the errors lel


class Main_Window(QWidget):
    def __init__(self):
        super(Main_Window, self).__init__()

        tabWidget = QTabWidget()
        tabWidget.addTab(MapTab(), 'Check Map')
        tabWidget.addTab(UserTab(), 'Screen User')
        tabWidget.addTab(UserOnMapTab(), 'Check User on Map')
        tabWidget.addTab(LocalTab(), 'Check Local Replays')
        tabWidget.addTab(VerifyTab(), 'Verify')

        edit = QTextEdit()
        edit.setReadOnly(True)
        edit.append('print("test")\ntest\necho this is fake lel\n'*20)

        mainLayout = QVBoxLayout()
        mainLayout.addWidget(tabWidget)
        mainLayout.addWidget(edit)
        self.setLayout(mainLayout)
        self.setWindowTitle(f'Circleguard gui !!WIP!! (backend version {__version__})')
        return


class UserTab(QWidget):
    def __init__(self):
        super(UserTab, self).__init__()
        self.info = QLabel(self)
        self.info.setText('This will compare a user\'s n top plays with the n Top plays of the corresponding Map')
        self.grid = QGridLayout()
        self.grid.addWidget(self.info, 0, 0, 1, 1)
        self.setLayout(self.grid)


class MapTab(QWidget):
    def __init__(self):
        super(MapTab, self).__init__()
        self.info = QLabel(self)
        self.info.setText('This will compare the n Top plays of a Map')
        self.grid = QGridLayout()
        self.grid.addWidget(self.info, 0, 0, 1, 1)
        self.setLayout(self.grid)


class UserOnMapTab(QWidget):
    def __init__(self):
        super(UserOnMapTab, self).__init__()
        self.info = QLabel(self)
        self.info.setText('This will compare a user\'s score with the n Top plays of a Map')
        self.grid = QGridLayout()
        self.grid.addWidget(self.info, 0, 0, 1, 1)
        self.setLayout(self.grid)


class LocalTab(QWidget):
    def __init__(self):
        super(LocalTab, self).__init__()
        self.info = QLabel(self)
        self.info.setText('This will verify replays')
        self.grid = QGridLayout()
        self.grid.addWidget(self.info, 0, 0, 1, 1)
        self.setLayout(self.grid)


class VerifyTab(QWidget):
    def __init__(self):
        super(VerifyTab, self).__init__()
        self.info = QLabel(self)
        self.info.setText('This will compare a user\'s score with the n Top plays of a Map')
        self.grid = QGridLayout()
        self.grid.addWidget(self.info, 0, 0, 1, 1)
        self.setLayout(self.grid)


if __name__ == '__main__':
    app = QApplication([])
    app.setStyle('Fusion')
    test_window = Main_Window()
    test_window.show()
    app.exec_()
