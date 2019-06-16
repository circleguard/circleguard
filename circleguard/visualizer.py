from circleguard import utils
from circleguard.enums import Mod

# pylint: disable=no-name-in-module
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QPoint
from PyQt5.QtWidgets import QWidget, QMainWindow, QGridLayout, QSlider, QPushButton, QStyle, QShortcut
from PyQt5.QtGui import QColor, QPainterPath, QPainter, QPen, QKeySequence
# pylint: enable=no-name-in-module

import osu_parser

WIDTH_LINE = 1
WIDTH_POINT = 3
WIDTH_CIRCLE_BORDER = 3
FRAMES_ON_SCREEN = 15 # how many frames for each replay to draw on screen at a time
                      # (though some will have high alpha values and be semi transparent)
PEN_BLUE = QPen(QColor(63, 127, 255))
PEN_RED = QPen(QColor(255, 127, 63))
PEN_BLACK = QPen(QColor(17, 17, 17))
DRAW_SIZE = 600 # square area
OSU_WINDOW_SIZE = 512 # a constant of the game
POS_MULT = DRAW_SIZE / OSU_WINDOW_SIZE # multiply each point by this


class Point(QPoint):
    """
    A sublcass of QPoint that acts solely to remove the need to multiply x and y
    by POS_MULT when creating a point.
    """
    def __init__(self, x, y):
        super().__init__(x * POS_MULT, y * POS_MULT)


class _Renderer(QWidget):
    update_signal = pyqtSignal(int)

    def __init__(self, replay1, replay2, beatmap_path, parent=None):
        super(_Renderer, self).__init__(parent)
        # initialize variables
        self.current_time = 0
        self.pos1 = -1 # so our first frame is at data[0] since we do pos + 1
        self.pos2 = -1
        self.buffer1 = []
        self.buffer2 = []
        self.buffer_additions1 = []
        self.buffer_additions2 = []
        self.hitobjs = []
        self.paused = False

        print("parsing beatmap")
        self.beatmap = osu_parser.from_path(beatmap_path)

        self.data1 = replay1.as_list_with_timestamps() #t,x,y
        self.data2 = replay2.as_list_with_timestamps() #t,x,y

        # flip replay if one is with hr
        mods1 = [Mod(mod_val) for mod_val in utils.bits(replay1.mods)]
        mods2 = [Mod(mod_val) for mod_val in utils.bits(replay2.mods)]
        flip1 = Mod.HardRock in mods1
        flip2 = Mod.HardRock in mods2
        if(flip1 ^ flip2): # xor, if one has hr but not the other
            for d in self.data1:
                d[1] = 384 - d[1] # flip the x's

        self.replay_len = max(len(self.data1), len(self.data2))
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

    def next_frame(self):
        """
        Adds frames to two buffer_additions variables. Every time this method is called both arrays are guaranteed
        to have at least one value added (after being cleared by paintEvent), but one may have more if there are frames
        between it and the larger time. See comments in this method for a more helpful walkthrough (hopefully)

        buffer_additions will be drawn by paintEvent in addition to the buffers, where buffer_additions are the latest
        replays and the buffers will have the oldest frames removed from them in equal amounts to the additions so that
        each buffer has at most FRAMES_ON_SCREEN (could have less if it's the start or the end; don't remove from buffer
        if it has less than FRAMES_ON_SCREEN)
        """

        #documentation assumes data arrays have time vals of
        # [3, 4, 6, 9] data1
        # [1, 2, 3.5, 7] data2
        next_frame1 = self.data1[self.pos1 + 1]
        next_frame2 = self.data2[self.pos2 + 1]
        next_time1 = next_frame1[0] # 3
        next_time2 = next_frame2[0] # 1
        print(next_time1)
        self.buffer_additions1.append(next_frame1)
        self.buffer_additions2.append(next_frame2)
        self.pos1 += 1
        self.pos2 += 1

        # if this enters, replay1 is the farther along
        while(next_time1 > next_time2): # 3 > 1
            self.pos2 += 1
            frame = self.data2[self.pos2]
            next_next_time2 = frame[0] # 2
            if(next_next_time2 > next_time1): # 2 ≯ 3 so don't enter
                break # only want to draw frames inbetweem the smaller and larger time, don't go over the larger time
            self.buffer_additions2.append(frame)
            next_time2 = next_next_time2 # next_time2 is now 2, loops again but next_next_time2
                                         # becomes 3.5 which is greater than next_time1 so we break

         # if first loop is entered (which it is in documentation) then this never should be
         # because of the break
         # if this enters, replay2 is farther along
        while(next_time2 > next_time1):
            self.pos1 += 1
            frame = self.data1[self.pos1]
            next_next_time1 = frame[0]
            if(next_next_time1 > next_time2):
                break
            self.buffer_additions1.append(frame)
            next_time1 = next_next_time1

        # if neither enter, both have the exact same next frame, so just draw both and call it a day

        # something is very off about this - the map is getting drawn starting from a farther time (instead of t=0
        # from the beamap's perspective), because the time in the replay and the time on the beatmap don't match up;
        # we can't really compare them directly like I do here unless I'm missing something.
        farthest_time = max(next_time1, next_time2)
        while farthest_time > (self.beatmap.next_time - 1000): # 1 second arbitrarily chosen
            hitobj = self.beatmap.advance()
            print(f"farthest time: {farthest_time}, hitobj time: {hitobj.time}")
            self.hitobjs.append(hitobj)

        # remove old hitojbects
        self.hitobjs = [hitobj for hitobj in self.hitobjs if hitobj.time > farthest_time - 1000]

        self.update_signal.emit(1)
        self.update()

    def paintEvent(self, event):
        """
        Called whenever self.update() is called
        """
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        self.paint_cursor(painter, self.buffer1, self.buffer_additions1)
        self.paint_cursor(painter, self.buffer2, self.buffer_additions2)
        self.paint_beatmap(painter)
        self.paint_info(painter)

    def paint_cursor(self, painter, buffer, buffer_additions):
        """
        Called whenever self.update() is called
        """
        buffer += buffer_additions

        # if less than FRAMES_ON_SCREEN, becomes 0. See https://math.stackexchange.com/a/3018840
        extra1 = int((abs(len(buffer) - FRAMES_ON_SCREEN) + (len(buffer) - FRAMES_ON_SCREEN)) / 2)

        del buffer[0:extra1]  # delete oldest extra frames

        alpha_step = 255/FRAMES_ON_SCREEN
        for i in range(len(buffer)-1):
            p1 = Point(buffer[i][1], buffer[i][2])
            p2 = Point(buffer[i+1][1], buffer[i+1][2])
            self.draw_line(painter, PEN_BLUE, i*alpha_step, p1, p2)
            self.draw_point(painter, PEN_BLUE, i*alpha_step, p1)
            if i == len(buffer)-2:
                self.draw_point(painter, PEN_BLUE, (i+1)*alpha_step, p2)

        buffer_additions.clear()

    def paint_beatmap(self, painter):
        # print(self.hitobjs)
        for hitobj in self.hitobjs:
            p = Point(hitobj.x, hitobj.y)
            self.draw_circle(painter, PEN_BLACK, 255, p, 10)

    def paint_info(self, painter):
        painter.setPen(QPen(QColor(128, 128, 128), 1))
        painter.drawText(0, 25, f"pos1: {self.pos1} | pos2: {self.pos2}")

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

        # I had pen.color().setAlpha(alpha), but it wouldn't actually change the alpha.
        # doing pen.setColor(pen.color()) after that didn't work either so I've resorted to
        # a possibly inefficient method by recreating the pen
        c = pen.color()
        pen_ = QPen(QColor(c.red(), c.green(), c.blue(), alpha))
        pen_.setWidth(WIDTH_LINE)
        painter.setPen(pen_)
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
        c = pen.color()
        pen_ = QPen(QColor(c.red(), c.green(), c.blue(), alpha))
        pen_.setWidth(WIDTH_POINT)
        painter.setPen(pen_)
        painter.drawPoint(point)

    def draw_circle(self, painter, pen, alpha, point, radius):
        """
        Draws an unfilled circle (the hit object in osu!) using the given painter, pen, and alpha level
        at the given QPoint with the given radius.

        Arguments:
            QPainter painter: The painter.
            QPen pen: The pen, containing the color of the circle border.
            Integer alpha: The alpha level from 0-255 to set the circle border to.
            QPoint point: The QPoint representing the coordinates at which to draw the circle.
            Integer radius: How large to draw the circle, in pixels
        """
        c = pen.color()
        pen_ = QPen(QColor(c.red(), c.green(), c.blue(), alpha))
        pen_.setWidth(WIDTH_CIRCLE_BORDER)
        painter.setPen(pen_)
        painter.drawEllipse(point, radius, radius) # qt wants ry and rx for ellipse, it doesn't provide a circle function


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
    def __init__(self, replay1, replay2, beatmap_path):
        super(_Interface, self).__init__()
        self.renderer = _Renderer(replay1, replay2, beatmap_path)
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
        self.slider.setStyleSheet("outline: none;") # get rid of distracting highlight outline when it's focused
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
    def __init__(self, replay1, replay2, beatmap_path):
        super(VisualizerWindow, self).__init__()
        self.interface = _Interface(replay1, replay2, beatmap_path)
        self.setCentralWidget(self.interface)
        self.setFixedSize(DRAW_SIZE, DRAW_SIZE)
        QShortcut(QKeySequence(Qt.Key_Space), self, self.interface.pause)
        QShortcut(QKeySequence(Qt.Key_Left), self, self.interface.previous_frame)
        QShortcut(QKeySequence(Qt.Key_Right), self, self.interface.next_frame)


    def closeEvent(self, event):
        super().closeEvent(event)
        self.interface.renderer.timer.stop()
