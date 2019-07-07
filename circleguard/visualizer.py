from circleguard import utils
from circleguard.enums import Mod

# pylint: disable=no-name-in-module
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QPointF
from PyQt5.QtWidgets import QWidget, QMainWindow, QGridLayout, QSlider, QPushButton, QStyle, QShortcut
from PyQt5.QtGui import QColor, QPainterPath, QPainter, QPen, QKeySequence
# pylint: enable=no-name-in-module

import osu_parser
import clock

WIDTH_LINE = 1
WIDTH_POINT = 3
WIDTH_CIRCLE_BORDER = 8
FRAMES_ON_SCREEN = 15  # how many frames for each replay to draw on screen at a time
PEN_BLUE = QPen(QColor(63, 127, 255))
PEN_RED = QPen(QColor(255, 127, 63))
PEN_BLACK = QPen(QColor(17, 17, 17))
PEN_WHITE = QPen(QColor(255, 255, 255))
X_OFFSET = 64
Y_OFFSET = 48
CURSOR_COLORS = [PEN_BLUE, PEN_RED]


class Point(QPointF):
    """
    A sublcass of QPoint that acts solely to remove the need to multiply x and y
    by POS_MULT when creating a point.
    """
    def __init__(self, x, y):
        super().__init__(x, y)


class _Renderer(QWidget):
    update_signal = pyqtSignal(int)

    def __init__(self, replays=(), beatmap_path="", parent=None):
        super(_Renderer, self).__init__(parent)
        # initialize variables
        self.setFixedSize(640, 480)
        self.replay_amount = len(replays)
        self.current_time = 0
        self.pos = [-1]*self.replay_amount  # so our first frame is at data[0] since we do pos + 1
        self.buffer = [[[0, 0, 0]],[[0,0,0]]]
        self.buffer_additions = [[[0, 0, 0]],[[0,0,0]]]
        self.clock = clock.Timer()
        self.hitobjs = []
        self.paused = False
        self.beatmap_path = beatmap_path
        if beatmap_path != "":
            self.beatmap = osu_parser.from_path(beatmap_path)
        self.data = []
        for replay in replays:
            self.data.append(replay.as_list_with_timestamps())  # t,x,y
        # flip all replays with hr
        for replay_index in range(len(replays)):
            for mods in utils.bits(replays[replay_index].mods):
                if Mod.HardRock is Mod(mods):
                    for d in self.data[replay_index]:
                        d[2] = 384 - d[2]

        self.replay_len = max((len(data) for data in self.data)) if self.replay_amount > 0 else 0
        self.next_frame()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.next_frame_from_timer)
        self.timer.start(1)  # 60fps (1000ms/60frames)

    def next_frame_from_timer(self):
        """
        Has the same effect as next_frame except if paused, where it returns. This is to allow
        the back/forward buttons to advance frame by frame while still paused (as they connect directly to next
        and previous frame), while still pausing the automatic timer advancement.
        """
        if self.paused:
            return
        self.next_frame()

    def search_timestamp(self, list_to_search, index, value, offset):
        """
        searches an array (:list_to_search:) for a :value: located at :index:.
        """
        found = offset
        # attempt to make efficient search
        for i in range(len(list_to_search)-offset):
            current = list_to_search[i+offset][index]
            try:
                next = list_to_search[i+offset+1][index]
            except IndexError:
                found = i+offset
                break
            if current < value < next:
                found = i+offset
                break
        return found

    def next_frame(self):
        """
        prepares next frame
        """
        current_time = self.clock.get_time()
        if self.replay_amount > 0:
            if current_time > self.data[0][-1][0]:  # resets visualizer if at end
                self.reset()

        for replay_index in range(self.replay_amount):
            self.pos[replay_index] = self.search_timestamp(self.data[replay_index], 0, current_time, self.pos[replay_index])
            magic = self.pos[replay_index] - FRAMES_ON_SCREEN if self.pos[replay_index] >= FRAMES_ON_SCREEN else 0
            self.buffer[replay_index] = self.data[replay_index][magic:self.pos[replay_index]]

        if self.beatmap_path != "":
            if self.beatmap.ar == 5:
                preempt = 1200
                fade_in = 800
            elif self.beatmap.ar < 5:
                preempt = 1200 + 600 * (5 - self.beatmap.ar) / 5
                fade_in = 800 + 400 * (5 - self.beatmap.ar) / 5
            else:
                preempt = 1200 - 750 * (self.beatmap.ar - 5) / 5
                fade_in = 800 - 500 * (self.beatmap.ar - 5) / 5

            hitwindow = 150 + 50 * (5 - self.beatmap.od) / 5
            # advance hitobjects
            while current_time+preempt > self.beatmap.next_time:
                hitobj = self.beatmap.advance()
                hitobj.preempt = preempt
                hitobj.fade_in = fade_in
                hitobj.hitwindow = hitwindow
                self.hitobjs.append(hitobj)
                hitobj.slider_body = []
                if hitobj.type == "slider":
                    res = len(hitobj.slider_info)*5
                    for i in range(0, res):
                        hitobj.slider_body.append(self.get_curve_point(i / res, hitobj.slider_info))

            # remove old hitobjects
            running_hitobjs = []
            for hitobj in self.hitobjs:
                if hitobj.type == "slider":
                    if hitobj.time+(hitobj.slider_length*hitobj.slider_repeats) > current_time:
                        running_hitobjs.append(hitobj)
                if hitobj.type == "circle":
                    if hitobj.time > current_time:
                        running_hitobjs.append(hitobj)
                if hitobj.type == "spinner":
                    if hitobj.spinner_length > current_time:
                        running_hitobjs.append(hitobj)
            self.hitobjs = running_hitobjs

            if self.beatmap.last_time < current_time:
                self.reset()
        self.update_signal.emit(1)
        self.update()

    def paintEvent(self, event):
        """
        Called whenever self.update() is called
        """
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        if self.beatmap_path != "":
            self.paint_beatmap(painter)
        self.paint_info(painter)
        for index in range(self.replay_amount):
            self.paint_cursor(painter, index)

    def paint_cursor(self, painter, index):
        """
        Called whenever self.update() is called
        """

        alpha_step = 255/FRAMES_ON_SCREEN
        for i in range(len(self.buffer[index])-1):
            self.draw_line(painter, CURSOR_COLORS[index], i*alpha_step, (self.buffer[index][i][1], self.buffer[index][i][2]), (self.buffer[index][i+1][1], self.buffer[index][i+1][2]))
            self.draw_point(painter, CURSOR_COLORS[index], i*alpha_step, (self.buffer[index][i][1], self.buffer[index][i][2]))
            if i == len(self.buffer[index])-2:
                self.draw_point(painter, CURSOR_COLORS[index], (i+1)*alpha_step, (self.buffer[index][i+1][1], self.buffer[index][i+1][2]))

    def paint_beatmap(self, painter):
        for hitobj in self.hitobjs[::-1]:
            self.draw_hitobject(painter, hitobj)

    def paint_info(self, painter):
        painter.setPen(QPen(QColor(128, 128, 128), 1))
        painter.drawText(0, 25, f"clock: {round(self.clock.get_time())}")

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

        c = pen.color()
        pen_ = QPen(QColor(c.red(), c.green(), c.blue(), alpha))
        pen_.setWidth(WIDTH_LINE)
        painter.setPen(pen_)
        painter.drawLine(start[0]+X_OFFSET, start[1]+Y_OFFSET, end[0]+X_OFFSET, end[1]+Y_OFFSET)

    def draw_point(self, painter, pen, alpha, point):
        c = pen.color()
        pen_ = QPen(QColor(c.red(), c.green(), c.blue(), alpha))
        pen_.setWidth(WIDTH_POINT)
        painter.setPen(pen_)
        painter.drawPoint(point[0]+X_OFFSET, point[1]+Y_OFFSET)

    def draw_hitobject(self, painter, hitobj):
        if hitobj.type == "circle":
            self.draw_hitcircle(painter, hitobj)
            self.draw_approachcircle(painter, hitobj)
        if hitobj.type == "slider":
            self.draw_slider(painter, hitobj)
        if hitobj.type == "spinner":
            self.draw_spinner(painter, hitobj)

    def draw_hitcircle(self, painter, hitobj):
        current_time = self.clock.get_time()
        hitcircle_alpha = 255-((hitobj.time - current_time - (hitobj.preempt-hitobj.fade_in))/hitobj.fade_in)*255
        hitcircle_alpha = hitcircle_alpha if hitcircle_alpha < 255 else 255
        c = PEN_WHITE.color()

        hircircle_radius = (384 / 16) * (1 - (0.7 * (self.beatmap.cs - 5) / 5))
        pen_ = QPen(QColor(c.red(), c.green(), c.blue(), hitcircle_alpha))
        pen_.setWidth(WIDTH_CIRCLE_BORDER)
        painter.setPen(pen_)
        painter.drawEllipse(hitobj.x-hircircle_radius+X_OFFSET, hitobj.y-hircircle_radius+Y_OFFSET, hircircle_radius*2, hircircle_radius*2)  # Qpoint placed it at the wrong position, no idea why

    def draw_spinner(self, painter, hitobj):
        current_time = self.clock.get_time()
        small_circle = (384 / 16) * (1 - (0.7 * (self.beatmap.cs - 5) / 5))
        big_circle = (384/2)

        hitcircle_alpha = 255-((hitobj.time - current_time - (hitobj.preempt-hitobj.fade_in))/hitobj.fade_in)*255
        hitcircle_alpha = hitcircle_alpha if hitcircle_alpha < 255 else 255

        spinner_scale = max(1-(hitobj.spinner_length - current_time)/(hitobj.spinner_length-hitobj.time), 0)
        c = PEN_WHITE.color()

        spinner_radius = small_circle+(big_circle*(1-spinner_scale))
        pen_ = QPen(QColor(c.red(), c.green(), c.blue(), hitcircle_alpha))
        pen_.setWidth(int(WIDTH_CIRCLE_BORDER/2))
        painter.setPen(pen_)
        painter.drawEllipse(512/2-spinner_radius+X_OFFSET, 384/2-spinner_radius+Y_OFFSET, spinner_radius*2, spinner_radius*2)  # Qpoint placed it at the wrong position, no idea why

    def draw_approachcircle(self, painter, hitobj):
        current_time = self.clock.get_time()
        hitcircle_alpha = 255-((hitobj.time - current_time - (hitobj.preempt-hitobj.fade_in))/hitobj.fade_in)*255
        hitcircle_alpha = hitcircle_alpha if hitcircle_alpha < 255 else 255
        approachcircle_scale = max(((hitobj.time - current_time)/hitobj.preempt)*4+1, 1)
        c = PEN_WHITE.color()

        approachcircle_radius = (384 / 16) * (1 - (0.7 * (self.beatmap.cs - 5) / 5))*approachcircle_scale
        pen_ = QPen(QColor(c.red(), c.green(), c.blue(), hitcircle_alpha))
        pen_.setWidth(int(WIDTH_CIRCLE_BORDER/2))
        painter.setPen(pen_)
        painter.drawEllipse(hitobj.x-approachcircle_radius+X_OFFSET, hitobj.y-approachcircle_radius+Y_OFFSET, approachcircle_radius*2, approachcircle_radius*2)  # Qpoint placed it at the wrong position, no idea why

    def draw_slider(self, painter, hitobj):
        current_time = self.clock.get_time()
        self.draw_sliderbody(painter, hitobj)
        if hitobj.time > current_time:
            self.draw_hitcircle(painter,hitobj)
            self.draw_approachcircle(painter,hitobj)

    def draw_sliderbody(self, painter, hitobj):
        sliderbody = QPainterPath()
        sliderbody_radius = (384 / 16) * (1 - (0.7 * (self.beatmap.cs - 5) / 5))

        _pen = painter.pen()
        _pen.setWidth(sliderbody_radius*2+WIDTH_CIRCLE_BORDER*2)
        _pen.setCapStyle(Qt.RoundCap)
        _pen.setJoinStyle(Qt.RoundJoin)
        _pen.setColor(QColor(255, 255, 255, 255))

        _pen_inside = QPen()
        _pen_inside.setWidth(sliderbody_radius*2+WIDTH_CIRCLE_BORDER)
        _pen_inside.setCapStyle(Qt.RoundCap)
        _pen_inside.setJoinStyle(Qt.RoundJoin)
        _pen_inside.setColor(QColor(73, 73, 73, 255))

        sliderbody.moveTo(hitobj.x+X_OFFSET, hitobj.y+Y_OFFSET)
        for i in hitobj.slider_body:
            sliderbody.lineTo(i[0]+X_OFFSET, i[1]+Y_OFFSET)

        sliderbody_inside = sliderbody
        painter.setPen(_pen)
        painter.drawPath(sliderbody)
        painter.setPen(_pen_inside)
        painter.drawPath(sliderbody_inside)

    @staticmethod
    def linear_interpolate(x1, x2, r):
        """
        Linearly interpolates coordinate tuples x1 and x2 with ratio r.

        Args:
            Float x1: The startpoint of the interpolation.
            Float x2: The endpoint of the interpolation.
            Float r: The ratio of the points to interpolate to.
        """

        return (1 - r) * x1[0] + r * x2[0], (1 - r) * x1[1] + r * x2[1]

    def get_curve_point(self, t, points):
        if len(points) == 1:
            return points[0]
        newpoints = []
        for i in range(len(points)-1):
            newpoints.append(self.linear_interpolate(points[i], points[i+1], t))
        return self.get_curve_point(t, newpoints)

    def reset(self):
        if self.beatmap_path != "":
            self.pos = [-1] * self.replay_amount
            self.beatmap.reset()
            self.hitobjs = []
        self.clock.reset()

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
    def __init__(self, replays=(), beatmap_path=""):
        super(_Interface, self).__init__()
        self.renderer = _Renderer(replays, beatmap_path)
        self.layout = QGridLayout()
        self.slider = QSlider(Qt.Horizontal)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.addWidget(self.renderer, 0, 0, 1, 10)
        self.setLayout(self.layout)

    def update_slider(self, delta_value):
        """
        Increases the slider's position by delta_value amount.

        Arguments:
            Integer delta_value: How much to increase the slider's value by.
        """
        self.slider.setValue(self.slider.value() + delta_value)

    # messy repeated code, there's got to be a better way to work around interface.pause always switching states
    # and the frame methods only ever pausing and never unpausing
    def previous_frame(self):
        if not self.renderer.paused:
            self.pause()
        self.run_button.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay if self.renderer.paused else QStyle.SP_MediaPause))
        self.renderer.seek_to(self.slider.value() - 1)

    def next_frame(self):
        if not self.renderer.paused:
            self.pause()
        self.run_button.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay if self.renderer.paused else QStyle.SP_MediaPause))
        self.renderer.seek_to(self.slider.value() + 1)

    def pause(self):
        self.renderer.pause()
        self.run_button.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay if self.renderer.paused else QStyle.SP_MediaPause))


class VisualizerWindow(QMainWindow):
    def __init__(self, replays=(), beatmap_path=""):
        super(VisualizerWindow, self).__init__()
        self.interface = _Interface(replays, beatmap_path)
        self.setCentralWidget(self.interface)
        self.setWindowFlag(Qt.MSWindowsFixedSizeDialogHint)  # resizing is not important rn
        QShortcut(QKeySequence(Qt.Key_Space), self, self.interface.pause)
        QShortcut(QKeySequence(Qt.Key_Left), self, self.interface.previous_frame)
        QShortcut(QKeySequence(Qt.Key_Right), self, self.interface.next_frame)

    def closeEvent(self, event):
        super().closeEvent(event)
        self.interface.renderer.timer.stop()
