
from circleguard import Replay
from circleguard import utils

import threading
# pylint: disable=no-name-in-module
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtWidgets import QWidget, QMainWindow, QGridLayout, QSlider, QPushButton, QStyle
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
        self.data1 = replay1.as_list_with_timestamps()
        self.data2 = replay2.as_list_with_timestamps()
        self.data1, self.data2 = utils.interpolate(self.data1, self.data2, unflip=False)
        self.data1 = utils.resample(self.data1, 60)
        self.data2 = utils.resample(self.data2, 60)
        self.data1 = [(512 - d[1], 384 - d[2]) for d in self.data1]
        self.data2 = [(512 - d[1], 384 - d[2]) for d in self.data2]
        self.replay_len = len(self.data1)
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

        self.buffer1 = self.data1[self.counter:self.counter+(int(10*self.old_multiplier))]
        # generate path 1
        # I'm pretty sure you can't change the pen while drawing a path,
        # so we either have different colors or one combined path object.
        self.path1 = QPainterPath()
        self.path1.moveTo(self.buffer1[0][0], self.buffer1[0][1])
        for item in self.buffer1:
            self.path1.lineTo(item[0], item[1])

        self.buffer2 = self.data2[self.counter:self.counter+(int(10*self.old_multiplier))]
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

        self.previous_button = QPushButton()
        self.previous_button.setIcon(self.style().standardIcon(QStyle.SP_MediaSkipBackward))
        self.previous_button.setFixedWidth(20)
        self.previous_button.setToolTip("Move to previous Frame")
        self.previous_button.clicked.connect(self.previous_frame)

        self.next_button = QPushButton()
        self.next_button.setIcon(self.style().standardIcon(QStyle.SP_MediaSkipForward))
        self.next_button.setFixedWidth(20)
        self.next_button.setToolTip("Move to next Frame")
        self.next_button.clicked.connect(self.next_frame)

        self.run_button = QPushButton()
        self.run_button.setIcon(self.style().standardIcon(QStyle.SP_MediaPause))
        self.run_button.setToolTip("Play/Pause playback")
        self.run_button.clicked.connect(self.pause)
        self.run_button.setFixedWidth(20)

        self.slider.setRange(0, self.renderer.replay_len)
        self.slider.setValue(0)
        self.slider.valueChanged.connect(self.renderer.seek_to)
        self.renderer.update_signal.connect(self.update_slider)

        self.layout.addWidget(self.renderer, 0, 0, 1, 10)
        self.layout.addWidget(self.previous_button, 1, 0, 1, 1)
        self.layout.addWidget(self.run_button, 1, 1, 1, 1)
        self.layout.addWidget(self.next_button, 1, 2, 1, 1)
        self.layout.addWidget(self.slider, 1, 3, 1, 7)
        self.setLayout(self.layout)

    def update_slider(self, new):
        self.slider.setValue(new)

    def previous_frame(self):
        if not self.renderer.paused:
            self.renderer.pause()
        self.slider.setValue(self.slider.value()-1)

    def next_frame(self):
        if not self.renderer.paused:
            self.renderer.pause()
        self.slider.setValue(self.slider.value()+1)

    def pause(self):
        self.renderer.pause()
        self.run_button.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay if self.renderer.paused else QStyle.SP_MediaPause))


class VisualizerWindow(QMainWindow):
    def __init__(self, replay1, replay2):
        super(VisualizerWindow, self).__init__()
        self.interface = _Interface(replay1, replay2)
        self.setCentralWidget(self.interface)
        self.setFixedSize(512, 512)

    def closeEvent(self, event):
        super().closeEvent(event)
        self.interface.renderer.timer.stop()
