import math
import time
import threading

from circleguard import utils
from circleguard.enums import Mod
from tempfile import TemporaryDirectory
from slider import Beatmap, Library
from slider.beatmap import Circle, Slider, Spinner
from slider.curve import Bezier, MultiBezier
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

__slider_dir = TemporaryDirectory()
SLIDER_LIBARY = Library.create_db(get_setting("cache_dir"))

class _Renderer(QWidget):
    update_signal = pyqtSignal(int)

    def __init__(self, replays=[], beatmap_id=None, beatmap_path=None, parent=None):
        super(_Renderer, self).__init__(parent)
        # initialize variables
        self.setFixedSize(640, 480)
        self.replay_amount = len(replays)
        self.pos = [0]*self.replay_amount
        self.buffer = [[[[0, 0, 0]]]*self.replay_amount][0]
        self.hitobjs = []
        self.data = []
        self.usernames = []
        self.paused = False
        self.beatmap_flag = False
        self.playback_len = 0
        self.play_direction = 1
        self.frame_times = []
        self.loading_flag = True
        self.sliders_total = 0
        self.sliders_current = 0
        self.last_frame = 0
        self.CURSOR_COLORS = [QPen(QColor().fromHslF(i/self.replay_amount,0.75,0.5)) for i in range(self.replay_amount)]
        
        if beatmap_path != None:
            self.beatmap = Beatmap.from_path(beatmap_path)
            self.beatmap_flag = True
            self.playback_len = self.beatmap.hit_objects[-1].time.total_seconds() * 1000+3000
        elif beatmap_id != None:
            print("beatmap_id passed")
            self.beatmap = SLIDER_LIBARY.lookup_by_id(beatmap_id, download=True, save=True)
            self.beatmap_flag = True
            self.playback_len = self.beatmap.hit_objects[-1].time.total_seconds() * 1000+3000
        else:
            print("no beatmap_id passed")

        for replay in replays:
            self.data.append(replay.as_list_with_timestamps())  # t,x,y
            self.usernames.append(replay.username)

        # flip all replays with hr
        try:
            for replay_index in range(len(replays)):
                for mods in utils.bits(replays[replay_index].mods):
                    if Mod.HardRock is Mod(mods):
                        for d in self.data[replay_index]:
                            d[2] = 384 - d[2]
        except ValueError:  # happens on exported auto plays
            pass

        self.playback_len = max(data[-1][0] for data in self.data) if self.replay_amount > 0 else self.playback_len
        # calc preempt, fade_in, hitwindow
        if self.beatmap.approach_rate == 5:
            self.preempt = 1200
        elif self.beatmap.approach_rate  < 5:
            self.preempt = 1200 + 600 * (5 - self.beatmap.approach_rate) / 5
        else:
            self.preempt = 1200 - 750 * (self.beatmap.approach_rate - 5) / 5
        self.hitwindow = 150 + 50 * (5 - self.beatmap.overall_difficulty) / 5
        self.fade_in = 400
        self.hitcircle_radius = ((109 - 9 * self.beatmap.circle_size)-WIDTH_CIRCLE_BORDER)/2
        # pre-calculate every slider
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.next_frame_from_timer)
        self.timer.start(1000/60)  # 60fps (1000ms/60frames)
        self.next_frame()
        self.thread = threading.Thread(target=self.proccess_sliders)
        self.thread.start()

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
        if self.loading_flag:
            self.update()
            return
        current_time = self.clock.get_time()
        if self.replay_amount > 0:
            if current_time > self.data[0][-1][0] or current_time < 0:  # resets visualizer if at end
                self.reset(end=True if self.clock.current_speed < 0 else False)

        current_time = self.clock.get_time()
        for replay_index in range(self.replay_amount):
            self.pos[replay_index] = self.search_timestamp(self.data[replay_index], 0, current_time, self.pos[replay_index])
            magic = self.pos[replay_index] - FRAMES_ON_SCREEN if self.pos[replay_index] >= FRAMES_ON_SCREEN else 0
            self.buffer[replay_index] = self.data[replay_index][magic:self.pos[replay_index]]

        if self.beatmap_flag:
            self.get_hitobjects()
            if self.beatmap.hit_objects[-1].time.total_seconds() * 1000+3000 < current_time:
                self.reset()
        self.update_signal.emit(current_time)
        self.update()

    def get_hitobjects(self):
        # get current hitobjects
        time = self.clock.get_time()
        found_all = False
        index = 0
        self.hitobjs = []
        while not found_all:
            current_hitobj = self.beatmap.hit_objects[index]
            hit_t = current_hitobj.time.total_seconds() * 1000
            if isinstance(current_hitobj, Slider) or isinstance(current_hitobj, Spinner):
                hit_end = self.get_hit_endtime(current_hitobj) + (self.fade_in)
            else:
                hit_end = hit_t + self.hitwindow + (self.fade_in)
            if hit_t-self.preempt < time < hit_end :
                self.hitobjs.append(current_hitobj)
            elif hit_t > time:
                found_all = True
            index += 1
            if index == len(self.beatmap.hit_objects)-1:
                found_all = True


    def paintEvent(self, event):
        """
        Called whenever self.update() is called. Draws all cursors and Hitobjects
        """
        painter = QPainter(self)
        painter.setRenderHint(QPainter.TextAntialiasing, True)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.HighQualityAntialiasing, True)
        black_bg = get_setting("visualizer_bg")
        painter.setPen(PEN_WHITE if (get_setting("dark_theme") or black_bg) else PEN_BLACK)
        _pen = painter.pen()
        if black_bg:
            pal = QPalette()
            pal.setColor(QPalette.Background, Qt.black)
            self.setAutoFillBackground(True)
            self.setPalette(pal)
        # loading screen
        if self.thread.is_alive():
            self.draw_loading_screen(painter)
            return
        elif self.loading_flag:
            self.loading_flag = False
            self.clock = clock.Timer()
            return
        # debug stuff
        self.frame_times.insert(0,self.clock.get_time()-self.last_frame)  # TODO remove multiplier or second clock
        self.frame_times = self.frame_times[:120]
        self.last_frame = self.clock.get_time()
        # actual visualizer
        if self.beatmap_flag:
            self.paint_beatmap(painter)
        for index in range(self.replay_amount):
            self.paint_cursor(painter, index)
        painter.setPen(_pen)
        if get_setting("visualizer_info"):
            self.paint_info(painter)
        if get_setting("visualizer_frametime"):
            self.paint_frametime_graph(painter)

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
    
    def paint_frametime_graph(self, painter):
        _pen = painter.pen()
        x_offset = 640
        c = _pen.color()
        painter.setBrush(QColor(255-c.red(),255-c.green(),255-c.blue(), 180))
        painter.drawRect(640-360, 480-100, 360,100)
        painter.setBrush(QColor(255-c.red(),255-c.green(),255-c.blue(), 0))
        # line routine, draws 60/30/15 fps lines
        c = _pen.color()
        _pen.setColor(QColor(c.red(), c.green(), c.blue(), c.alpha()/2))
        painter.setPen(_pen)
        ref_path = QPainterPath()
        ref_path.moveTo(x_offset-360, 480-17)
        ref_path.lineTo(x_offset, 480-17)
        ref_path.moveTo(x_offset-360, 480-33)
        ref_path.lineTo(x_offset, 480-33)
        ref_path.moveTo(x_offset-360, 480-67)
        ref_path.lineTo(x_offset, 480-67)
        painter.drawPath(ref_path)
        # draw frame time graph
        _pen.setColor(QColor(c.red(), c.green(), c.blue(), c.alpha()))
        painter.setPen(_pen)
        frame_path = QPainterPath()
        frame_path.moveTo(x_offset, max(380,480-(self.frame_times[0])))
        for time in self.frame_times:
            x_offset -= 3
            frame_path.lineTo(x_offset, max(380,480-(time)))
        painter.drawPath(frame_path)

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
        if isinstance(hitobj, Circle):
            self.draw_hitcircle(painter, hitobj)
            self.draw_approachcircle(painter, hitobj)
        if isinstance(hitobj, Slider):
            self.draw_slider(painter, hitobj) # TODO hitobj.tick_points for sliderball
        if isinstance(hitobj, Spinner):
            self.draw_spinner(painter, hitobj)

    def draw_hitcircle(self, painter, hitobj):
        """
        Draws Hitcircle.

        Args:
            QPainter painter: The painter.
            Hitobj hitobj: A Hitobject.
        """
        current_time = self.clock.get_time()
        fade_out_scale = max(0,((current_time - self.get_hit_time(hitobj))/self.hitwindow*0.75))
        hitcircle_alpha = 255-((self.get_hit_time(hitobj) - current_time - (self.preempt-self.fade_in))/self.fade_in)*255
        magic = (255*(fade_out_scale))
        hitcircle_alpha = hitcircle_alpha if hitcircle_alpha < 255 else 255
        hitcircle_alpha = hitcircle_alpha - (magic if magic > 0 else 0)
        hitcircle_alpha = hitcircle_alpha if hitcircle_alpha > 0 else 0
        c = painter.pen().color()
        p = hitobj.position
        _pen = QPen(QColor(c.red(), c.green(), c.blue(), hitcircle_alpha))
        _pen.setWidth(WIDTH_CIRCLE_BORDER)
        painter.setPen(_pen)
        painter.setBrush(QBrush(QColor(c.red(),c.green(),c.blue(),int(hitcircle_alpha/4))))  # fill hitcircle
        painter.drawEllipse(p.x-self.hitcircle_radius+X_OFFSET, p.y-self.hitcircle_radius+Y_OFFSET, self.hitcircle_radius*2, self.hitcircle_radius*2)  # Qpoint placed it at the wrong position, no idea why
        painter.setBrush(QBrush(QColor(c.red(),c.green(),c.blue(),0)))

    def draw_spinner(self, painter, hitobj):
        """
        Draws Spinner.

        Args:
            QPainter painter: The painter.
            Hitobj hitobj: A Hitobject.
        """
        current_time = self.clock.get_time()
        big_circle = (384/2)
        hitcircle_alpha = 255-((self.get_hit_time(hitobj) - current_time - (self.preempt-self.fade_in))/self.fade_in)*255
        fade_out = max(0,((current_time - self.get_hit_endtime(hitobj))/self.hitwindow*0.5))
        magic = (75*((fade_out)*2))
        hitcircle_alpha = hitcircle_alpha if hitcircle_alpha < 255 else 255
        hitcircle_alpha = hitcircle_alpha - (magic if magic > 0 else 0)
        hitcircle_alpha = hitcircle_alpha if hitcircle_alpha > 0 else 0
        
        spinner_scale = max(1-(self.get_hit_endtime(hitobj)- current_time)/(self.get_hit_endtime(hitobj) - self.get_hit_time(hitobj)), 0)
        c = painter.pen().color()

        spinner_radius = self.hitcircle_radius+(big_circle*(1-spinner_scale))
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
        if self.get_hit_time(hitobj) - current_time < 0: return
        hitcircle_alpha = 255-((self.get_hit_time(hitobj) - current_time - (self.preempt-self.fade_in))/self.fade_in)*255
        hitcircle_alpha = hitcircle_alpha if hitcircle_alpha < 255 else 255
        approachcircle_scale = max(((self.get_hit_time(hitobj)  - current_time)/self.preempt)*3+1, 1)
        c = painter.pen().color()
        p = hitobj.position
        approachcircle_radius = self.hitcircle_radius * approachcircle_scale
        _pen = QPen(QColor(c.red(), c.green(), c.blue(), hitcircle_alpha))
        _pen.setWidth(int(WIDTH_CIRCLE_BORDER/2))
        painter.setPen(_pen)
        painter.drawEllipse(p.x-approachcircle_radius+X_OFFSET, p.y-approachcircle_radius+Y_OFFSET, approachcircle_radius*2, approachcircle_radius*2)  # Qpoint placed it at the wrong position, no idea why

    def draw_slider(self, painter, hitobj):
        """
        Draws sliderbody and hitcircle & approachcircle if needed

        Args:
            QPainter painter: The painter.
            Hitobj hitobj: A Hitobject.
        """
        self.draw_sliderbody(painter, hitobj)
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
        sliderbody_alpha = 75-((self.get_hit_time(hitobj) - current_time - (self.preempt-self.fade_in))/self.fade_in)*75
        fade_out = max(0,((current_time - self.get_hit_endtime(hitobj))/self.hitwindow*0.5))
        magic = (75*((fade_out)*2))
        sliderbody_alpha = sliderbody_alpha if sliderbody_alpha < 75 else 75
        sliderbody_alpha = sliderbody_alpha - (magic if magic > 0 else 0)
        sliderbody_alpha = sliderbody_alpha if sliderbody_alpha > 0 else 0
        c = painter.pen().color()

        _pen = painter.pen()
        _pen.setWidth(self.hitcircle_radius*2+WIDTH_CIRCLE_BORDER)
        _pen.setCapStyle(Qt.RoundCap)
        _pen.setJoinStyle(Qt.RoundJoin)
        _pen.setColor(QColor(c.red(), c.green(), c.blue(), sliderbody_alpha))

        p = hitobj.position
        sliderbody.moveTo(p.x+X_OFFSET, p.y+Y_OFFSET)
        for i in hitobj.slider_body:
            sliderbody.lineTo(i.x+X_OFFSET, i.y+Y_OFFSET)

        painter.setPen(_pen)
        painter.drawPath(sliderbody)

    def draw_progressbar(self, painter, percentage):
        loading_bg = QPainterPath()
        loading_bar = QPainterPath()
        c = painter.pen().color()

        _pen = painter.pen()
        _pen.setWidth(5)
        _pen.setCapStyle(Qt.RoundCap)
        _pen.setJoinStyle(Qt.RoundJoin)
        _pen.setColor(QColor(c.red(), c.green(), c.blue(), 25))
        painter.setPen(_pen)

        loading_bg.moveTo(250, 260)
        loading_bg.lineTo(250 + 150, 260)

        loading_bar.moveTo(250, 260)
        loading_bar.lineTo(250 + percentage*1.5, 260)

        painter.drawPath(loading_bg)
        _pen.setColor(QColor(c.red(), c.green(), c.blue(), 255))
        painter.setPen(_pen)
        painter.drawPath(loading_bar)

    def draw_loading_screen(self, painter):
        painter.drawText(250, 250, f"Calculating Sliders, please wait...")
        self.draw_progressbar(painter,int((self.sliders_current/self.sliders_total)*100))

    def proccess_sliders(self):
        self.sliders_total = len(self.beatmap.hit_objects)-1
        for index in range(len(self.beatmap.hit_objects)):
            self.sliders_current = index
            current_hitobj = self.beatmap.hit_objects[index]
            if isinstance(current_hitobj, Slider):
                    try:
                        current_hitobj.slider_body
                    except:
                        if isinstance(current_hitobj.curve,Bezier):  # unsure if this is needed
                            self.beatmap.hit_objects[index].slider_body = [current_hitobj.curve.at(i/64) for i in range(64)]
                        elif isinstance(current_hitobj.curve,MultiBezier):
                            self.beatmap.hit_objects[index].slider_body = [current_hitobj.curve(i/64) for i in range(64)]  # TODO calc points needed with length
                        else:
                            self.beatmap.hit_objects[index].slider_body = current_hitobj.curve.points

    
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
            next_frames = [self.data[x][self.pos[x]][0] for x in range(len(self.data))]
            self.seek_to(min(next_frames))
        else:
            previous_frames = [self.data[x][self.pos[x]-1][0] for x in range(len(self.data))]
            self.seek_to(min(previous_frames)-1)

    def seek_to(self, position):
        """
        Seeks to position if the change is bigger than ± 10.
        Also calls next_frame() so the correct frame is displayed.

        Args:
            Integer position: position to seek to in ms
        """
        if not position-10 < self.clock.time_counter < position+10:
            self.clock.time_counter = position
            if self.paused:
                self.next_frame()

    def get_hit_endtime(self, hitobj):
        return hitobj.end_time.total_seconds() * 1000

    def get_hit_time(self, hitobj):
        return hitobj.time.total_seconds() * 1000

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
    def __init__(self, replays=[], beatmap_id=None, beatmap_path=None):
        super(_Interface, self).__init__()
        self.renderer = _Renderer(replays, beatmap_id, beatmap_path)

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
        self.slider.valueChanged.connect(self.renderer.seek_to)

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
            self.renderer.resume()
        else:
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
    def __init__(self, replays=[], beatmap_id=None, beatmap_path=None):
        super(VisualizerWindow, self).__init__()
        self.setWindowTitle("Visualizer")
        self.setWindowIcon(QIcon(str(resource_path("resources/logo.ico"))))
        self.interface = _Interface(replays, beatmap_id, beatmap_path)
        self.setCentralWidget(self.interface)
        self.setWindowFlag(Qt.MSWindowsFixedSizeDialogHint)  # resizing is not important rn
        QShortcut(QKeySequence(Qt.Key_Space), self, self.interface.pause)
        QShortcut(QKeySequence(Qt.Key_Left), self, self.interface.previous_frame)
        QShortcut(QKeySequence(Qt.Key_Right), self, self.interface.next_frame)

    def closeEvent(self, event):
        super().closeEvent(event)
        self.interface.renderer.timer.stop()
        np.seterr(**PREVIOUS_ERRSTATE)
