from circleguard import utils
from circleguard.enums import Mod


# pylint: disable=no-name-in-module
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QPoint
from PyQt5.QtWidgets import QWidget, QMainWindow, QGridLayout, QSlider, QPushButton, QStyle
from PyQt5.QtGui import QColor, QPainterPath, QPainter, QPen
# pylint: enable=no-name-in-module

WIDTH_LINE = 1
WIDTH_POINT = 3

PEN_BLUE = QPen(QColor(63, 127, 255))
PEN_RED = QPen(QColor(255, 127, 63))

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
        mods1 = [Mod(mod_val) for mod_val in utils.bits(replay1.mods)]
        mods2 = [Mod(mod_val) for mod_val in utils.bits(replay2.mods)]
        flip1 = Mod.HardRock in mods1
        flip2 = Mod.HardRock in mods2
        if(flip1 ^ flip2): # xor, if one has hr but not the other
            for d in self.data1:
                d[1] = 384 - d[1]

        self.replay_len = len(self.data1)
        self.timer.timeout.connect(self.next_frame_from_timer)
        self.timer.start(1000/60)  # 60fps (1000ms/60frames)
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
        alpha_step = 255/len(self.buffer2)
        for i in range(len(self.buffer1)-1):
            p1 = QPoint(self.buffer1[i][1], self.buffer1[i][2])
            p2 = QPoint(self.buffer1[i+1][1], self.buffer1[i+1][2])
            self.draw_line(painter, PEN_BLUE, i*alpha_step, p1, p2)

        for i in range(len(self.buffer2)-1):
            p1 = QPoint(self.buffer2[i][1], self.buffer2[i][2])
            p2 = QPoint(self.buffer2[i+1][1], self.buffer2[i+1][2])
            self.draw_line(painter, PEN_RED, i*alpha_step, p1, p2)

        for i in range(len(self.buffer1)):
            p = QPoint(self.buffer1[i][1], self.buffer1[i][2])
            self.draw_point(painter, PEN_BLUE, i*alpha_step, p)

        for i in range(len(self.buffer2)):
            p = QPoint(self.buffer2[i][1], self.buffer2[i][2])
            self.draw_point(painter, PEN_RED, i*alpha_step, p)

        painter.setPen(QPen(QColor(128, 128, 128), 1))
        painter.drawText(0, 25, f"frame: {self.current} | frame change : {str(self.frame_change).rjust(3,'0')} | step was at replay{self.chosen_replay}")

    def draw_line(self, painter, pen, alpha, start, end):
        """
        Draws a line using the given painter, pen, and alpha level from Point start to Point end.

        Arguments:
            QPainter painter: The painter.
            QPen pen: The pen, containing the color of the line.
            Integer alpha: The alpha level from 0-255 to set the line to.
                           https://doc.qt.io/qt-5/qcolor.html#alpha-blended-drawing
            QPoint start: The start of the line.
            QPoint end: The end of the line.
        """
        pen.setWidth(WIDTH_LINE)
        pen.color().setAlpha(alpha)
        painter.setPen(pen)
        painter.drawLine(start, end)

    def draw_point(self, painter, pen, alpha, point):
        """
        Draws a point using the given painter, pen, and alpha level at the given QPoint.

        Arguments:
            QPainter painter: The painter.
            QPen pen: The pen, containing the color of the point.
            Integer alpha: The alpha level from 0-255 to set the point to.
            QPoint point: The QPoint representing the coordinates at which to draw the point.
        """
        pen.setWidth(WIDTH_POINT)
        pen.color().setAlpha(alpha)
        painter.setPen(pen)
        painter.drawPoint(point)


    def next_frame_from_timer(self):
        """
        Has the same effect as next_frame except if paused, where it returns. This is to allow
        the back/forward buttons to advance frame by frame while still paused (as they connect directly to next
        and previous frame), while still pausing the automatic timer advancement.
        """
        if self.paused:
            return
        self.next_frame()

    def next_frame(self):
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
        self.buffer1 = self.data1[self.counter1:self.counter1 + 15]
        self.buffer2 = self.data2[self.counter2:self.counter2 + 15]
        self.update_signal.emit(1)
        self.update()

    def reset(self):
        self.counter1 = 0
        self.counter2 = 0
        self.current = 0

    def seek_to(self, position):
        """
        TODO Doesn't actually seek to a position, just advances the frame.
        This and previous_frame are both effectively broken right now
        """
        self.next_frame()

    def pause(self):
        """
        Switches the current paused state of the visualizer.
        """
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
        self.previous_button.setToolTip("Retreat Frame")
        self.previous_button.clicked.connect(self.previous_frame)

        self.next_button = QPushButton()
        self.next_button.setIcon(self.style().standardIcon(QStyle.SP_MediaSkipForward))
        self.next_button.setFixedWidth(20)
        self.next_button.setToolTip("Advance Frame")
        self.next_button.clicked.connect(self.next_frame)

        self.run_button = QPushButton()
        self.run_button.setIcon(self.style().standardIcon(QStyle.SP_MediaPause))
        self.run_button.setToolTip("Play/Pause")
        self.run_button.clicked.connect(self.pause)
        self.run_button.setFixedWidth(20)

        self.slider.setRange(0, self.renderer.replay_len)
        self.slider.setValue(0)
        self.renderer.update_signal.connect(self.update_slider)

        self.layout.addWidget(self.renderer, 0, 0, 1, 10)
        self.layout.addWidget(self.previous_button, 1, 0, 1, 1)
        self.layout.addWidget(self.run_button, 1, 1, 1, 1)
        self.layout.addWidget(self.next_button, 1, 2, 1, 1)
        self.layout.addWidget(self.slider, 1, 3, 1, 7)
        self.setLayout(self.layout)

    def update_slider(self, delta_value):
        """
        Increases the slider's position by delta_value amount.

        Arguments:
            Integer delta_value: How much to increase the slider's value by
        """
        self.slider.setValue(self.slider.value() + delta_value)

    def previous_frame(self):
        if not self.renderer.paused:
            self.renderer.pause()
        self.renderer.seek_to(self.slider.value() - 1)

    def next_frame(self):
        if not self.renderer.paused:
            self.renderer.pause()
        self.renderer.seek_to(self.slider.value() + 1)

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
