from circleguard import enums
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
        self.current = 0
        self.frame_change = 0
        self.counter1 = 0
        self.counter2 = 0
        self.chosen_replay = -1
        self.buffer1 = []
        self.buffer2 = []
        self.paused = False
        self.path1 = QPainterPath()
        self.path2 = QPainterPath()
        self.timer = QTimer(self)
        # interpolate replays
        self.data1 = replay1.as_list_with_timestamps()
        self.data2 = replay2.as_list_with_timestamps()
        # flip replay if one is with hr
        bit_values_gen1 = self.bits(replay1.mods)
        bit_values_gen2 = self.bits(replay2.mods)
        self.enabled_mods_replay_1 = frozenset(enums.Mod(mod_val) for mod_val in bit_values_gen1)
        self.enabled_mods_replay_2 = frozenset(enums.Mod(mod_val) for mod_val in bit_values_gen2)
        flip1 = enums.Mod.HardRock.value in [mod.value for mod in self.enabled_mods_replay_1]
        flip2 = enums.Mod.HardRock.value in [mod.value for mod in self.enabled_mods_replay_2]
        if flip1 ^ flip2:
            self.data1 = [(d[0], 512 - d[1], d[2]) for d in self.data1]
        else:
            self.data1 = [(d[0], 512 - d[1], 384 - d[2]) for d in self.data1]
        self.data2 = [(d[0], 512 - d[1], 384 - d[2]) for d in self.data2]
        self.replay_len = len(self.data1)
        self.timer.timeout.connect(self.next_frame)
        self.timer.start(1000/60)  # next frame every 1/60sec
        self.next_frame()

    @staticmethod
    def bits(n):
        if n == 0:
            yield 0
        while n:
            b = n & (~n + 1)
            yield b
            n ^= b

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
        alpha_step = 255/len(self.buffer2)
        for i in range(len(self.buffer1)-1):
            painter.setPen(QPen(QColor(63, 127, 255, (i*alpha_step)), 1))
            painter.drawLine(self.buffer1[i][1], self.buffer1[i][2], self.buffer1[i+1][1], self.buffer1[i+1][2])
        for i in range(len(self.buffer2)-1):
            painter.setPen(QPen(QColor(255, 127, 63, (i*alpha_step)), 1))
            painter.drawLine(self.buffer2[i][1], self.buffer2[i][2], self.buffer2[i+1][1], self.buffer2[i+1][2])

        for i in range(len(self.buffer1)):
            painter.setPen(QPen(QColor(255, 127, 63, (i*alpha_step)), 3))
            painter.drawPoint(int(self.buffer1[i][1]), int(self.buffer1[i][2]))

        for i in range(len(self.buffer2)):
            painter.setPen(QPen(QColor(63, 127, 255, (i*alpha_step)), 3))
            painter.drawPoint(int(self.buffer2[i][1]), int(self.buffer2[i][2]))
        painter.setPen(QPen(QColor(128, 128, 128), 1))
        painter.drawText(0, 25, f"frame: {self.current} | frame change : {str(self.frame_change).rjust(3,'0')} | step was at replay{self.chosen_replay}")

    def next_frame(self):
        if self.paused:
            return
        self.current += int(1000/120)  # this is completely wrong but it kinda works, sooooo
        next_frame_1 = self.data1[self.counter1 + 1][0]
        next_frame_2 = self.data2[self.counter2 + 1][0]

        # plan is to skip frames in the past
        while next_frame_1 < self.current or next_frame_2 < self.current:
            self.counter1 += 1
            self.counter2 += 1
            next_frame_1 = self.data1[self.counter1+1][0]
            next_frame_2 = self.data2[self.counter2+1][0]

        if next_frame_1 == next_frame_2:
            self.chosen_replay = "1&2"
            self.frame_change = 0
            self.current = next_frame_1
            self.counter1 += 1
            self.counter2 += 1
        elif next_frame_1 < next_frame_2:
            self.chosen_replay = 1
            self.frame_change = next_frame_1-self.current
            self.current = next_frame_1
            self.counter1 += 1
        else:
            self.chosen_replay = 2
            self.frame_change = next_frame_2-self.current
            self.current = next_frame_2
            self.counter2 += 1
        self.buffer1 = self.data1[self.counter1:self.counter1+(int(15))]
        self.buffer2 = self.data2[self.counter2:self.counter2+(int(15))]
        self.update()

    def reset(self):
        self.counter1 = 0
        self.counter2 = 0
        self.current = 0

    def seek_to(self, position):
        return position
        """
        if self.paused:
            self.paused = False
            self.next_frame()
            self.paused = True
        """

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
