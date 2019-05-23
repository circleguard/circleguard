from replay import Replay
import threading
# pylint: disable=no-name-in-module
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtWidgets import QWidget, QMainWindow, QGridLayout, QSlider, QPushButton
from PyQt5.QtGui import QColor, QPainterPath, QPainter, QPen
# pylint: enable=no-name-in-module


class _Renderer(QWidget):
    update_signal = pyqtSignal(int)

    def __init__(self, replay1, replay2, parent=None):
        super(_Renderer, self).__init__(parent)
        # initialize variables
        self.counter = 0
        self.old_multiplier = 1
        self.buffer1 = []
        self.buffer2 = []
        self.paused = False
        self.path1 = QPainterPath()
        self.path2 = QPainterPath()
        self.timer = QTimer(self)
        # interpolate replays
        self.replay1 = Replay(replay1, "replay1", 0)
        self.replay2 = Replay(replay2, "replay2", 0)  # todo pass mods/usernames
        self.replay1 = self.replay1.as_list_with_timestamps()
        self.replay2 = self.replay2.as_list_with_timestamps()
        self.replay1, self.replay2 = Replay.interpolate(self.replay1, self.replay2, unflip=False)
        self.replay1 = Replay.skip_breaks(self.replay1)
        self.replay2 = Replay.skip_breaks(self.replay2)
        self.replay1 = Replay.resample(self.replay1, 60)
        self.replay2 = Replay.resample(self.replay2, 60)
        self.replay1 = [(512 - d[1], 384 - d[2]) for d in self.replay1]
        self.replay2 = [(512 - d[1], 384 - d[2]) for d in self.replay2]
        self.replay_len = len(self.replay1)
        print(f"replay is {self.replay_len/60} seconds long")

        self.timer.timeout.connect(self.next_frame)
        self.timer.start(1000/60)  # next frame every 1/60sec
        self.next_frame()

    def paintEvent(self, event):  # finished
        """
        painter3 = QPainter(self)
        image = QImage("C:/Users/Master/Documents/GitHub/circleguard-script/circleguard/resources/logo.png")
        painter3.drawImage(self.width() / 2 - 100, self.height() / 2 - 100, image)  # sprite example
        image = image.scaled(20, 20, Qt.KeepAspectRatio)  # sprite resize example
        painter3.drawImage(0, 0, image)  # sprite example
        painter3.drawImage(self.width() - 20, self.height() - 20, image)  # sprite example
        painter3.drawImage(0, self.height() - 20, image)  # sprite example
        painter3.drawImage(self.width() - 20, 0, image)  # sprite example
        """
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        painter.setPen(QPen(QColor(63, 127, 255), 1))
        painter.drawPath(self.path1)

        painter.setPen(QPen(QColor(255, 127, 63), 1))
        painter.drawPath(self.path2)

        # todo this is next section is wrong, since we should draw the raw events and not the interpolated events
        painter.setPen(QPen(QColor(255, 127, 63), 3))
        for i in self.buffer1:
            painter.drawPoint(int(i[0]), int(i[1]))

        painter.setPen(QPen(QColor(63, 127, 255), 3))
        for i in self.buffer2:
            painter.drawPoint(int(i[0]), int(i[1]))

    def next_frame(self):  # finished
        if self.paused:
            return
        if self.counter >= self.replay_len-1:
            self.reset()

        self.buffer1 = self.replay1[self.counter:self.counter+(int(10*self.old_multiplier))]
        # generate path 1
        # I'm pretty sure you can't change the pen while drawing a path,
        # so we either have different colors or one combined path object.
        self.path1 = QPainterPath()
        self.path1.moveTo(self.buffer1[0][0], self.buffer1[0][1])
        for item in self.buffer1:
            self.path1.lineTo(item[0], item[1])

        self.buffer2 = self.replay2[self.counter:self.counter+(int(10*self.old_multiplier))]
        # generate path 2
        self.path2 = QPainterPath()
        self.path2.moveTo(self.buffer2[0][0], self.buffer2[0][1])
        for item in self.buffer2:
            self.path2.lineTo(item[0], item[1])
        self.update()
        self.update_signal.emit(self.counter)
        self.counter += 1

    def reset(self):
        self.counter = 0

    def seek_to(self, kek):
        self.counter = kek
        if self.paused:
            self.paused = False
            self.next_frame()
            self.paused = True

    def pause(self):
        if self.paused:
            self.paused = False
        else:
            self.paused = True


class _Interface(QWidget):
    def __init__(self, replay1, replay2):
        super(_Interface, self).__init__()
        self.renderer = _Renderer(replay1, replay2)
        self.layout = QGridLayout()
        self.slider = QSlider(Qt.Horizontal)

        self.slider.setRange(0, self.renderer.replay_len)
        self.slider.setValue(0)
        self.slider.valueChanged.connect(self.renderer.seek_to)
        self.renderer.update_signal.connect(self.update_slider)

        self.run_button = QPushButton()
        self.run_button.setText("Play/Pause")
        self.run_button.clicked.connect(self.renderer.pause)

        self.layout.addWidget(self.renderer)
        self.layout.addWidget(self.slider)
        self.layout.addWidget(self.run_button)
        self.setLayout(self.layout)

    def update_slider(self, new):
        self.slider.setValue(new)


class VisualizerWindow(QMainWindow):
    def __init__(self, replay1, replay2):
        super(VisualizerWindow, self).__init__()
        self.interface = _Interface(replay1, replay2)
        self.setCentralWidget(self.interface)
        self.setFixedSize(512, 512)

    def closeEvent(self, event):
        super().closeEvent(event)
        self.interface.renderer.timer.stop()
