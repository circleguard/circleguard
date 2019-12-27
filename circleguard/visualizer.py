import math
import time

from circleguard import utils, Mod
from circleparse.beatmap import Beatmap
# pylint: disable=no-name-in-module
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QPointF
from PyQt5.QtWidgets import QWidget, QMainWindow, QGridLayout, QSlider, QPushButton, QShortcut, QLabel
from PyQt5.QtGui import QColor, QPainterPath, QPainter, QPen, QKeySequence, QIcon, QPalette, QBrush
# pylint: enable=no-name-in-module

import clock
from utils import resource_path
from settings import get_setting

import math

import numpy as np
PREVIOUS_ERRSTATE = np.seterr('raise')

WIDTH_LINE = 1
WIDTH_POINT = 3
WIDTH_CIRCLE_BORDER = 8
FRAMES_ON_SCREEN = 15  # how many frames for each replay to draw on screen at a time
PEN_BLACK = QPen(QColor(17, 17, 17))
PEN_WHITE = QPen(QColor(255, 255, 255))
X_OFFSET = 64
Y_OFFSET = 48
SPEED_OPTIONS = [0.10, 0.25, 0.50, 0.75, 1.00, 1.25, 1.50, 2.00, 5.00, 10.00]


class _Renderer(QWidget):
    update_signal = pyqtSignal(int)

    def __init__(self, replays=[], beatmap_path="", parent=None):
        super(_Renderer, self).__init__(parent)
        # initialize variables
        self.setFixedSize(640, 480)
        self.replay_amount = len(replays)
        self.current_time = 0
        self.pos = [1]*self.replay_amount  # so our first frame is at data[0] since we do pos + 1
        self.buffer = [[[[0, 0, 0]]]*self.replay_amount][0]
        self.buffer_additions = [[[[0, 0, 0]]]*self.replay_amount][0]
        self.clock = clock.Timer()
        self.last_time = time.time_ns()
        self.hitobjs = []
        self.paused = False
        self.beatmap_path = beatmap_path
        self.CURSOR_COLORS = [QPen(QColor().fromHslF(i/self.replay_amount,0.75,0.5)) for i in range(self.replay_amount)]
        self.playback_len = 0
        if beatmap_path != "":
            self.beatmap = Beatmap(beatmap_path)
            self.playback_len = self.beatmap.hitobjects[-1].time
        self.data = []
        self.usernames = []
        for replay in replays:
            self.data.append(replay.as_list_with_timestamps())  # t,x,y
            self.usernames.append(replay.username)
        # flip all replays with hr
        for i, replay in enumerate(replays):
            if Mod.HR in replay.mods:
                for d in self.data[i]:
                    d[2] = 384 - d[2]

        self.play_direction = 1
        self.playback_len = max(data[-1][0] for data in self.data) if self.replay_amount > 0 else self.playback_len
        self.next_frame()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.next_frame_from_timer)
        self.timer.start(1000/60)  # 60fps (1000ms/60frames)

    def next_frame_from_timer(self):
        """
        Has the same effect as next_frame except if paused, where it returns. This is to allow
        the back/forward buttons to advance frame by frame while still paused (as they connect directly to next
        and previous frame), while still pausing the automatic timer advancement.
        """
        if self.paused:
            return
        self.next_frame()

    def search_timestamp(self, array, index, value, offset):
        """
        Searches an (:array:) for a :value: located in column :index:,
        assuming the data is monotonically increasing.

        Args:
            list array: A list of List which contain the timestamp at index
            Integer index: The column index of the timestamp
            Float value: The value to search for.
            Integer offset: Position of the timestamp to start the search from.
        """

        direction = self.play_direction

        if array[offset][index] <= value:
            high = len(array) - 1
            low = offset
            mid = low
            value = int(math.ceil(value))
        else:
            high = offset
            low = 0
            mid = high
            value = int(value)

        while array[high][index] != array[low][index]:
            if value < array[low][index]:
                return low if direction > 0 else low - 1
            elif value > array[high][index]:
                return high - 1 if direction > 0 else high

            try:
                mid = low + (value - array[low][index]) * (high - low) // (array[high][index] - array[low][index])
            except:
                mid = low + (value - array[low][index]) / (array[high][index] - array[low][index]) * (high - low)
                mid = int(mid)

            if array[mid][index] < value:
                low = mid + 1
            elif array[mid][index] > value:
                high = mid - 1
            else:
                return mid

        return low

    def next_frame(self):
        """
        prepares next frame
        """
        current_time = self.clock.get_time()
        if self.replay_amount > 0:
            if current_time > self.data[0][-1][0] or current_time < 0:  # resets visualizer if at end
                self.reset(end=True if self.clock.current_speed < 0 else False)

        current_time = self.clock.get_time()
        for replay_index in range(self.replay_amount):
            self.pos[replay_index] = self.search_timestamp(self.data[replay_index], 0, current_time, self.pos[replay_index])
            magic = self.pos[replay_index] - FRAMES_ON_SCREEN if self.pos[replay_index] >= FRAMES_ON_SCREEN else 0
            self.buffer[replay_index] = self.data[replay_index][magic:self.pos[replay_index]]

        if self.beatmap_path != "":
            self.get_hitobjects()
            if self.beatmap.hitobjects[-1].time+3000 < current_time:
                self.reset()
        self.update_signal.emit(current_time)
        self.update()

    def get_hitobjects(self):
        # calc preempt, fade_in, hitwindow
        if self.beatmap.difficulty["ApproachRate"] == 5:
            preempt = 1200
            fade_in = 800
        elif self.beatmap.difficulty["ApproachRate"] < 5:
            preempt = 1200 + 600 * (5 - self.beatmap.difficulty["ApproachRate"]) / 5
            fade_in = 800 + 400 * (5 - self.beatmap.difficulty["ApproachRate"]) / 5
        else:
            preempt = 1200 - 750 * (self.beatmap.difficulty["ApproachRate"] - 5) / 5
            fade_in = 800 - 500 * (self.beatmap.difficulty["ApproachRate"] - 5) / 5
        hitwindow = 150 + 50 * (5 - self.beatmap.difficulty["OverallDifficulty"]) / 5

        # get current hitobjects
        time = self.clock.get_time()
        found_all = False
        index = 0
        self.hitobjs = []
        while not found_all:
            current_hitobj = self.beatmap.hitobjects[index]
            if current_hitobj.time-preempt < time < current_hitobj.time or ((current_hitobj.time-preempt < time < current_hitobj.time + current_hitobj.duration) if 2 & current_hitobj.type else False):  #
                current_hitobj.preempt = preempt
                current_hitobj.fade_in = fade_in
                current_hitobj.hitwindow = hitwindow
                self.hitobjs.append(current_hitobj)
            elif current_hitobj.time-preempt > time and not 2 & current_hitobj.type:
                found_all = True
            index += 1
            if index == len(self.beatmap.hitobjects)-1:
                found_all = True


    def paintEvent(self, event):
        """
        Called whenever self.update() is called. Draws all cursors and Hitobjects
        """
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        black_bg = get_setting("visualizer_bg")
        painter.setPen(PEN_WHITE if (get_setting("dark_theme") or black_bg) else PEN_BLACK)
        if black_bg:
            pal = QPalette()
            pal.setColor(QPalette.Background, Qt.black)
            self.setAutoFillBackground(True)
            self.setPalette(pal)
        if get_setting("visualizer_info"):
            self.paint_info(painter)
        if self.beatmap_path != "":
            self.paint_beatmap(painter)
        for index in range(self.replay_amount):
            self.paint_cursor(painter, index)

    def paint_cursor(self, painter, index):
        """
        Draws a cursor.

        Arguments:
            QPainter painter: The painter.
            Integer index: The index of the cursor to be drawn.
        """
        alpha_step = 255/FRAMES_ON_SCREEN
        for i in range(len(self.buffer[index])-1):
            self.draw_line(painter, self.CURSOR_COLORS[index], i*alpha_step, (self.buffer[index][i][1], self.buffer[index][i][2]), (self.buffer[index][i+1][1], self.buffer[index][i+1][2]))
            self.draw_point(painter, self.CURSOR_COLORS[index], i*alpha_step, (self.buffer[index][i][1], self.buffer[index][i][2]))
            if i == len(self.buffer[index])-2:
                self.draw_point(painter, self.CURSOR_COLORS[index], (i+1)*alpha_step, (self.buffer[index][i+1][1], self.buffer[index][i+1][2]))

    def paint_beatmap(self, painter):
        for hitobj in self.hitobjs[::-1]:
            self.draw_hitobject(painter, hitobj)

    def paint_info(self, painter):
        """
        Draws various Information.

        Args:
           QPainter painter: The painter.
        """
        _pen = painter.pen()
        painter.drawText(0, 15, f"Clock: {round(self.clock.get_time())} ms")
        if self.replay_amount > 0:
            for i in range(self.replay_amount):
                painter.setPen(self.CURSOR_COLORS[i])
                if len(self.buffer[i]) > 0:  # skips empty buffers
                    painter.drawText(0, 30+(15*i), f"Cursor {self.usernames[i]}: {int(self.buffer[i][-1][1])}, {int(self.buffer[i][-1][2])}")
                else:
                    painter.drawText(0, 30+(15*i), f"Cursor {self.usernames[i]}: Not yet loaded")
            painter.setPen(_pen)
            if self.replay_amount == 2:
                try:
                    distance = math.sqrt(((self.buffer[i-1][-1][1] - self.buffer[i][-1][1]) ** 2) + ((self.buffer[i-1][-1][2] - self.buffer[i][-1][2]) ** 2))
                    painter.drawText(0, 45 + (15 * i), f"Cursor Distance {self.usernames[i-1]}-{self.usernames[i]}: {int(distance)}px")
                except IndexError:  # Edge case where we only have data from one cursor
                    pass

    def draw_line(self, painter, pen, alpha, start, end):
        """
        Draws a line using the given painter, pen, and alpha level from Point start to Point end.

        Arguments:
            QPainter painter: The painter.
            QPen pen: The pen, containing the color of the line.
            Integer alpha: The alpha level from 0-255 to set the line to.
                           https://doc.qt.io/qt-5/qcolor.html#alpha-blended-drawing
            List start: The X&Y position of the start of the line.
            List end: The X&Y position of the end of the line.
        """

        c = pen.color()
        _pen = QPen(QColor(c.red(), c.green(), c.blue(), alpha))
        _pen.setWidth(WIDTH_LINE)
        painter.setPen(_pen)
        painter.drawLine(start[0]+X_OFFSET, start[1]+Y_OFFSET, end[0]+X_OFFSET, end[1]+Y_OFFSET)

    def draw_point(self, painter, pen, alpha, point):
        """
        Draws a line using the given painter, pen, and alpha level from Point start to Point end.

        Args:
           QPainter painter: The painter.
           QPen pen: The pen, containing the color of the line.
           Integer alpha: The alpha level from 0-255 to set the line to.
           List point: The X&Y position of the point.
        """
        c = pen.color()
        _pen = QPen(QColor(c.red(), c.green(), c.blue(), alpha))
        _pen.setWidth(WIDTH_POINT)
        painter.setPen(_pen)
        painter.drawPoint(point[0]+X_OFFSET, point[1]+Y_OFFSET)

    def draw_hitobject(self, painter, hitobj):
        """
        Calls corresponding functions to draw a Hitobjecz.

        Args:
            QPainter painter: The painter.
            Hitobj hitobj: A Hitobject.
        """
        if 1 & hitobj.type:
            self.draw_hitcircle(painter, hitobj)
            self.draw_approachcircle(painter, hitobj)
        if 2 & hitobj.type:
            self.draw_slider(painter, hitobj)

    def draw_hitcircle(self, painter, hitobj):
        """
        Draws Hitcircle.

        Args:
            QPainter painter: The painter.
            Hitobj hitobj: A Hitobject.
        """
        current_time = self.clock.get_time()
        hitcircle_alpha = 255-((hitobj.time - current_time - (hitobj.preempt-hitobj.fade_in))/hitobj.fade_in)*255
        hitcircle_alpha = hitcircle_alpha if hitcircle_alpha < 255 else 255
        c = painter.pen().color()

        hircircle_radius = (109 - 9 * self.beatmap.difficulty["CircleSize"])/2
        _pen = QPen(QColor(c.red(), c.green(), c.blue(), hitcircle_alpha))
        _pen.setWidth(WIDTH_CIRCLE_BORDER)
        painter.setPen(_pen)
        painter.setBrush(QBrush(QColor(c.red(),c.green(),c.blue(),int(hitcircle_alpha/4))))  # fill hitcircle
        painter.drawEllipse(hitobj.x-hircircle_radius+X_OFFSET, hitobj.y-hircircle_radius+Y_OFFSET, hircircle_radius*2, hircircle_radius*2)  # Qpoint placed it at the wrong position, no idea why
        painter.setBrush(QBrush(QColor(c.red(),c.green(),c.blue(),0)))

    def draw_spinner(self, painter, hitobj):
        """
        Draws Spinner.

        Args:
            QPainter painter: The painter.
            Hitobj hitobj: A Hitobject.
        """
        current_time = self.clock.get_time()
        small_circle = (109 - 9 * self.beatmap.difficulty["CircleSize"])/2
        big_circle = (384/2)

        hitcircle_alpha = 255-((hitobj.time - current_time - (hitobj.preempt-hitobj.fade_in))/hitobj.fade_in)*255
        hitcircle_alpha = hitcircle_alpha if hitcircle_alpha < 255 else 255

        spinner_scale = max(1-(hitobj.spinner_length - current_time)/(hitobj.spinner_length-hitobj.time), 0)
        c = painter.pen().color()

        spinner_radius = small_circle+(big_circle*(1-spinner_scale))
        _pen = QPen(QColor(c.red(), c.green(), c.blue(), hitcircle_alpha))
        _pen.setWidth(int(WIDTH_CIRCLE_BORDER/2))
        painter.setPen(_pen)
        painter.drawEllipse(512/2-spinner_radius+X_OFFSET, 384/2-spinner_radius+Y_OFFSET, spinner_radius*2, spinner_radius*2)  # Qpoint placed it at the wrong position, no idea why

    def draw_approachcircle(self, painter, hitobj):
        """
        Draws Approachcircle.

        Args:
            QPainter painter: The painter.
            Hitobj hitobj: A Hitobject.
        """
        current_time = self.clock.get_time()
        hitcircle_alpha = 255-((hitobj.time - current_time - (hitobj.preempt-hitobj.fade_in))/hitobj.fade_in)*255
        hitcircle_alpha = hitcircle_alpha if hitcircle_alpha < 255 else 255
        approachcircle_scale = max(((hitobj.time - current_time)/hitobj.preempt)*4+1, 1)
        c = painter.pen().color()

        approachcircle_radius = (109 - 9 * self.beatmap.difficulty["CircleSize"])/2*approachcircle_scale
        _pen = QPen(QColor(c.red(), c.green(), c.blue(), hitcircle_alpha))
        _pen.setWidth(int(WIDTH_CIRCLE_BORDER/2))
        painter.setPen(_pen)
        painter.drawEllipse(hitobj.x-approachcircle_radius+X_OFFSET, hitobj.y-approachcircle_radius+Y_OFFSET, approachcircle_radius*2, approachcircle_radius*2)  # Qpoint placed it at the wrong position, no idea why

    def draw_slider(self, painter, hitobj):
        """
        Draws sliderbody and hitcircle & approachcircle if needed

        Args:
            QPainter painter: The painter.
            Hitobj hitobj: A Hitobject.
        """
        current_time = self.clock.get_time()
        self.draw_sliderbody(painter, hitobj)
        if hitobj.time > current_time:
            self.draw_hitcircle(painter,hitobj)
            self.draw_approachcircle(painter,hitobj)

    def draw_sliderbody(self, painter, hitobj):
        """
        Draws a sliderbody using a QpainterPath.

        Args:
            QPainter painter: The painter.
            Hitobj hitobj: A Hitobject.
        """
        sliderbody = QPainterPath()
        current_time = self.clock.get_time()
        sliderbody_radius = (109 - 9 * self.beatmap.difficulty["CircleSize"])/2
        sliderbody_alpha = 75-((hitobj.time - current_time - (hitobj.preempt-hitobj.fade_in))/hitobj.fade_in)*75
        sliderbody_alpha = sliderbody_alpha if sliderbody_alpha < 75 else 75
        c = painter.pen().color()

        _pen = painter.pen()
        _pen.setWidth(sliderbody_radius*2+WIDTH_CIRCLE_BORDER)
        _pen.setCapStyle(Qt.RoundCap)
        _pen.setJoinStyle(Qt.RoundJoin)
        _pen.setColor(QColor(c.red(), c.green(), c.blue(), sliderbody_alpha))

        sliderbody.moveTo(hitobj.x+X_OFFSET, hitobj.y+Y_OFFSET)
        for i in hitobj.curve_points:
            sliderbody.lineTo(i.x+X_OFFSET, i.y+Y_OFFSET)

        painter.setPen(_pen)
        painter.drawPath(sliderbody)

    def reset(self, end=False):
        """
        Reset Visualization. If end is passed, the function will reset to the end of the map,
        setting the clock to the the max of the cursor data.

        Args:
            Boolean end: Moves everything to the end of the cursor data.
        """
        if end:
            self.pos = [len(self.data[0])-1, len(self.data[1])-1]
            self.clock.reset()
            self.clock.time_counter = int(self.data[0][-1][0])
        else:
            self.pos = [0] * self.replay_amount
            self.clock.reset()
        if self.paused:
            self.clock.pause()

    def search_nearest_frame(self, reverse=False):
        """
        Searches next frame in the corresponding direction.
        It gets a list of timestamps at the current position for every cursor and chooses the nearest one.

        Args:
            Boolean reverse: chooses the search direction
        """
        if not reverse:
            # len(self.data) is the number of replays being visualized
            # self.data[0] is for the first replay, as is self.pos[0]
            # self.pos is a list of current indecies of the replays
            # self.data[0][self.pos[0]] is the current frame we're on
            # so seek to the next frame; self.pos[0] + 1
            next_frame_times = [self.data[x][self.pos[x] + 1][0] for x in range(len(self.data))]
            self.seek_to(min(next_frame_times))
        else:
            previous_frame_times = [self.data[x][self.pos[x] - 1][0] for x in range(len(self.data))]
            self.seek_to(min(previous_frame_times)-1)

    def seek_to(self, position):
        """
        Seeks to position if the change is bigger than ± 10.
        Also calls next_frame() so the correct frame is displayed.

        Args:
            Integer position: position to seek to in ms
        """
        self.clock.time_counter = position
        if self.paused:
            self.next_frame()

    def pause(self):
        """
        Set paused flag and pauses the clock.
        """
        self.paused = True
        self.clock.pause()

    def resume(self):
        """
        Removes paused flag and resumes the clock.
        """
        self.paused = False
        self.clock.resume()


class _Interface(QWidget):
    def __init__(self, replays=[], beatmap_path=""):
        super(_Interface, self).__init__()
        self.renderer = _Renderer(replays, beatmap_path)

        self.layout = QGridLayout()
        self.slider = QSlider(Qt.Horizontal)

        self.play_reverse_button = QPushButton()
        self.play_reverse_button.setIcon(QIcon(str(resource_path("./resources/play_reverse.png"))))
        self.play_reverse_button.setFixedSize(20, 20)
        self.play_reverse_button.setToolTip("Plays visualization in reverse")
        self.play_reverse_button.clicked.connect(self.play_reverse)

        self.play_normal_button = QPushButton()
        self.play_normal_button.setIcon(QIcon(str(resource_path("./resources/play_normal.png"))))
        self.play_normal_button.setFixedSize(20, 20)
        self.play_normal_button.setToolTip("Plays visualization in normally")
        self.play_normal_button.clicked.connect(self.play_normal)

        self.next_frame_button = QPushButton()
        self.next_frame_button.setIcon(QIcon(str(resource_path("./resources/frame_next.png"))))
        self.next_frame_button.setFixedSize(20, 20)
        self.next_frame_button.setToolTip("Displays next frame")
        self.next_frame_button.clicked.connect(self.next_frame)

        self.previous_frame_button = QPushButton()
        self.previous_frame_button.setIcon(QIcon(str(resource_path("./resources/frame_back.png"))))
        self.previous_frame_button.setFixedSize(20, 20)
        self.previous_frame_button.setToolTip("Displays previous frame")
        self.previous_frame_button.clicked.connect(self.previous_frame)

        self.pause_button = QPushButton()
        self.pause_button.setIcon(QIcon(str(resource_path("./resources/pause.png"))))
        self.pause_button.setFixedSize(20, 20)
        self.pause_button.setToolTip("Pause visualization")
        self.pause_button.clicked.connect(self.pause)

        self.speed_up_button = QPushButton()
        self.speed_up_button.setIcon(QIcon(str(resource_path("./resources/speed_up.png"))))
        self.speed_up_button.setFixedSize(20, 20)
        self.speed_up_button.setToolTip("Speed up")
        self.speed_up_button.clicked.connect(self.increase_speed)

        self.speed_down_button = QPushButton()
        self.speed_down_button.setIcon(QIcon(str(resource_path("./resources/speed_down.png"))))
        self.speed_down_button.setFixedSize(20, 20)
        self.speed_down_button.setToolTip("Speed down")
        self.speed_down_button.clicked.connect(self.lower_speed)

        self.slider.setRange(0, self.renderer.playback_len)
        self.slider.setValue(0)
        self.slider.setFixedHeight(20)
        self.slider.setStyleSheet("outline: none;")
        self.renderer.update_signal.connect(self.update_slider)
        # don't want to use valueChanged because we change the value
        # programatically and valueChanged would cause a feedback loop.
        # sliderMoved only activates on true user action, when we actually
        # want to seek.
        self.slider.sliderMoved.connect(self.renderer.seek_to)

        self.speed_label = QLabel("1.00")
        self.speed_label.setFixedSize(40, 20)
        self.speed_label.setAlignment(Qt.AlignCenter | Qt.AlignVCenter)

        self.layout.addWidget(self.renderer, 0, 0, 16, 17)
        self.layout.addWidget(self.play_reverse_button, 17, 0, 1, 1)
        self.layout.addWidget(self.previous_frame_button, 17, 1, 1, 1)
        self.layout.addWidget(self.pause_button, 17, 2, 1, 1)
        self.layout.addWidget(self.next_frame_button, 17, 3, 1, 1)
        self.layout.addWidget(self.play_normal_button, 17, 4, 1, 1)
        self.layout.addWidget(self.slider, 17, 5, 1, 9)
        self.layout.addWidget(self.speed_label, 17, 14, 1, 1)
        self.layout.addWidget(self.speed_down_button, 17, 15, 1, 1)
        self.layout.addWidget(self.speed_up_button, 17, 16, 1, 1)
        self.setLayout(self.layout)

    def play_normal(self):
        self.renderer.resume()
        self.renderer.play_direction = 1
        self._update_speed()

    def update_slider(self, value):
        self.slider.setValue(value)

    def play_reverse(self):
        self.renderer.resume()
        self.renderer.play_direction = -1
        self._update_speed()

    def _update_speed(self):
        self.renderer.clock.change_speed(float(self.speed_label.text())*self.renderer.play_direction)

    def previous_frame(self):
        self.renderer.pause()
        self.renderer.search_nearest_frame(reverse=True)

    def next_frame(self):
        self.renderer.pause()
        self.renderer.search_nearest_frame(reverse=False)

    def pause(self):
        if(self.renderer.paused):
            self.pause_button.setIcon(QIcon(str(resource_path("./resources/pause.png"))))
            self.renderer.resume()
        else:
            self.pause_button.setIcon(QIcon(str(resource_path("./resources/play.png"))))
            self.renderer.pause()

    def lower_speed(self):
        index = SPEED_OPTIONS.index(float(self.speed_label.text()))
        if index != 0:
            self.speed_label.setText(str(SPEED_OPTIONS[index-1]))
            self._update_speed()

    def increase_speed(self):
        index = SPEED_OPTIONS.index(float(self.speed_label.text()))
        if index != len(SPEED_OPTIONS)-1:
            self.speed_label.setText(str(SPEED_OPTIONS[index+1]))
            self._update_speed()


class VisualizerWindow(QMainWindow):
    def __init__(self, replays=[], beatmap_path=""):
        super(VisualizerWindow, self).__init__()
        self.setWindowTitle("Visualizer")
        self.setWindowIcon(QIcon(str(resource_path("resources/logo.ico"))))
        self.interface = _Interface(replays, beatmap_path)
        self.setCentralWidget(self.interface)
        self.setWindowFlag(Qt.MSWindowsFixedSizeDialogHint)  # resizing is not important rn
        QShortcut(QKeySequence(Qt.Key_Space), self, self.interface.pause)
        QShortcut(QKeySequence(Qt.Key_Left), self, self.interface.previous_frame)
        QShortcut(QKeySequence(Qt.Key_Right), self, self.interface.next_frame)

    def closeEvent(self, event):
        super().closeEvent(event)
        self.interface.renderer.timer.stop()
        np.seterr(**PREVIOUS_ERRSTATE)
