import threading

from circleguard import Mod, Keys
from slider import Beatmap, Library
from slider.beatmap import Circle, Slider, Spinner
from slider.curve import Bezier, MultiBezier
from slider.mod import circle_radius, od_to_ms
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QPointF
from PyQt5.QtWidgets import QWidget, QFrame, QMainWindow, QGridLayout, QSlider, QPushButton, QShortcut, QLabel
from PyQt5.QtGui import QColor, QPainterPath, QPainter, QPen, QKeySequence, QIcon, QPalette, QBrush

import clock
from utils import resource_path, Player
from settings import get_setting, set_setting

import math

import numpy as np

PREVIOUS_ERRSTATE = np.seterr('raise')

WIDTH_LINE = 1
WIDTH_CROSS = 6
WIDTH_CIRCLE_BORDER = 8
FRAMES_ON_SCREEN = 15  # how many frames for each replay to draw on screen at a time
PEN_WHITE = QPen(QColor(200, 200, 200))
PEN_GRAY = QPen(QColor(75, 75, 75))
PEN_BLANK = QPen(QColor(0, 0, 0, 0))
BRUSH_GRAY = QBrush(QColor(100, 100, 100))
BRUSH_DARKGRAY = QBrush(QColor(10, 10, 10))
BRUSH_BLANK = QBrush(QColor(0, 0, 0, 0))
X_OFFSET = 64 + 192
Y_OFFSET = 48 + 48
SCREEN_WIDTH = 640 + 384
SCREEN_HEIGHT = 480 + 96


class _Renderer(QFrame):
    update_signal = pyqtSignal(int)

    def __init__(self, replays=[], beatmap_id=None, beatmap_path=None, parent=None, speed=1):
        super(_Renderer, self).__init__(parent)
        self.setMinimumSize(SCREEN_WIDTH, SCREEN_HEIGHT)
        self.painter = QPainter()

        # beatmap init stuff
        self.hitobjs = []
        if beatmap_path is not None:
            self.beatmap = Beatmap.from_path(beatmap_path)
            self.has_beatmap = True
            self.playback_len = self.get_hit_endtime(self.beatmap.hit_objects[-1])
        elif beatmap_id is not None:
            self.beatmap = Library(get_setting("cache_dir")).lookup_by_id(beatmap_id, download=True, save=True)
            self.has_beatmap = True
            self.playback_len = self.get_hit_endtime(self.beatmap.hit_objects[-1])
        else:
            self.playback_len = 0
            self.has_beatmap = False
        if not get_setting("render_beatmap"):
            self.has_beatmap = False
        # beatmap stuff
        if self.has_beatmap:
            # values taken from https://github.com/ppy/osu-wiki/blob/master/meta/unused/difficulty-settings.md
            # but it was taken from the osu! wiki since then so this might be a bit incorrect.
            if self.beatmap.approach_rate == 5:
                self.preempt = 1200
            elif self.beatmap.approach_rate < 5:
                self.preempt = 1200 + 600 * (5 - self.beatmap.approach_rate) / 5
            else:
                self.preempt = 1200 - 750 * (self.beatmap.approach_rate - 5) / 5
            self.hitwindow = od_to_ms(self.beatmap.overall_difficulty).hit_50
            self.fade_in = 400
            self.hitcircle_radius = circle_radius(self.beatmap.circle_size) - WIDTH_CIRCLE_BORDER / 2
            ## loading stuff
            self.is_loading = True
            self.sliders_total = 0
            self.sliders_current = 0
            self.thread = threading.Thread(target=self.process_sliders)
            self.thread.start()
        else:
            self.is_loading = False

        # replay stuff
        self.replay_amount = len(replays)
        self.players = []
        for replay in replays:
            self.players.append(
                Player(data=np.array(replay.as_list_with_timestamps()),
                       replay=replay,
                       username=replay.username,
                       mods=replay.mods.short_name(),
                       buffer=[],
                       cursor_color=QPen(QColor().fromHslF(replays.index(replay) / self.replay_amount, 0.75, 0.5)),
                       pos=0))
        self.playback_len = max(player.data[-1][0] for player in self.players) if self.replay_amount > 0 else self.playback_len
        # flip all replays with hr
        for player in self.players:
            if Mod.HardRock in player.replay.mods:
                for d in player.data:
                    d[2] = 384 - d[2]

        # clock stuff
        self.clock = clock.Timer(speed)
        self.paused = False
        self.play_direction = 1

        # debug stuff
        self.frame_time_clock = clock.Timer(1)
        self.last_frame = 0
        self.frame_times = []

        # render stuff
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.next_frame_from_timer)
        self.timer.start(1000/60) # 62 fps (1000ms/60frames but the result can only be a integer)
        self.next_frame()

        # black background
        pal = QPalette()
        pal.setColor(QPalette.Background, Qt.black)
        self.setAutoFillBackground(True)
        self.setPalette(pal)

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
        prepares next frame
        """
        # just update the frame if currently loading
        if self.is_loading:
            self.update()
            return

        current_time = self.clock.get_time()
        # resets visualizer if at end
        if current_time > self.playback_len or current_time < 0:
            self.reset(end=True if self.clock.current_speed < 0 else False)

        for player in self.players:
            player.pos = np.searchsorted(player.data.T[0], current_time, "right")
            magic = player.pos - FRAMES_ON_SCREEN if player.pos >= FRAMES_ON_SCREEN else 0
            player.buffer = player.data[magic:player.pos]

        if self.has_beatmap:
            self.get_hitobjects()
        self.update_signal.emit(current_time)
        self.update()

    def get_hitobjects(self):
        # get current hitobjects
        current_time = self.clock.get_time()
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
            if hit_t - self.preempt < current_time < hit_end:
                self.hitobjs.append(current_hitobj)
            elif hit_t > current_time:
                found_all = True
            if index == len(self.beatmap.hit_objects) - 1:
                found_all = True
            index += 1

    def paintEvent(self, event):
        """
        Called whenever self.update() is called. Draws all cursors and Hitobjects
        """
        self.painter.begin(self)
        self.painter.setRenderHint(QPainter.TextAntialiasing, True)
        self.painter.setRenderHint(QPainter.Antialiasing, True)
        self.painter.setPen(PEN_WHITE)
        _pen = self.painter.pen()
        # loading screen
        if self.is_loading:
            if self.thread.is_alive():
                self.draw_loading_screen()
                self.painter.end()
                return
            else:
                self.is_loading = False
                self.clock.reset()
                self.painter.end()
                return
        # debug stuff
        self.frame_times.insert(0, self.frame_time_clock.get_time() - self.last_frame)
        self.frame_times = self.frame_times[:120]
        self.last_frame = self.frame_time_clock.get_time()
        # beatmap
        if self.has_beatmap:
            self.paint_beatmap()
        # cursors
        for player in self.players:
            self.paint_cursor(player)
        # other info
        self.painter.setPen(_pen)
        if get_setting("visualizer_info"):
            self.paint_info()
        if get_setting("visualizer_frametime"):
            self.paint_frametime_graph()
        self.painter.end()

    def paint_cursor(self, player):
        """
        Draws a cursor.

        Arguments:
            QPainter painter: The painter.
            Integer index: The index of the cursor to be drawn.
        """
        alpha_step = 1 / FRAMES_ON_SCREEN
        _pen = player.cursor_color
        _pen.setWidth(WIDTH_LINE)
        self.painter.setPen(_pen)
        for i in range(len(player.buffer) - 1):
            self.draw_line(i * alpha_step, (player.buffer[i][1], player.buffer[i][2]),
                                           (player.buffer[i + 1][1], player.buffer[i + 1][2]))
        _pen.setWidth(2)
        self.painter.setPen(_pen)
        for i in range(len(player.buffer) - 1):
            self.draw_cross(i * alpha_step, (player.buffer[i][1], player.buffer[i][2]))
            if i == len(player.buffer) - 2:
                self.draw_cross((i + 1) * alpha_step, (player.buffer[i + 1][1], player.buffer[i + 1][2]))
        # reset alpha
        self.painter.setOpacity(1)

    def paint_beatmap(self):
        for hitobj in self.hitobjs[::-1]:
            self.draw_hitobject(hitobj)

    def paint_info(self):
        """
        Draws various Information.

        Args:
           QPainter painter: The painter.
        """
        PEN_WHITE.setWidth(1)
        self.painter.setPen(PEN_WHITE)
        self.painter.setOpacity(0.25)
        self.painter.drawRect(X_OFFSET, Y_OFFSET, 512, 384)
        self.painter.setOpacity(1)
        self.painter.drawText(5, 15, f"Clock: {round(self.clock.get_time())} ms | Cursor count: {len(self.players)}")
        if self.replay_amount > 0:
            for i in range(len(self.players)):
                player = self.players[i]
                p = player.cursor_color
                self.painter.setPen(PEN_BLANK)
                self.painter.setBrush(QBrush(p.color()))
                if len(player.buffer) > 0: # skips empty buffers
                    self.painter.setOpacity(1 if Keys.M1 in Keys(int(player.buffer[-1][3])) else 0.3)
                    self.painter.drawRect(5, 27 - 9 + (11 * i), 10, 10)
                    self.painter.setOpacity(1 if Keys.M2 in Keys(int(player.buffer[-1][3])) else 0.3)
                    self.painter.drawRect(18, 27 - 9 + (11 * i), 10, 10)
                    self.painter.setOpacity(1)
                    self.painter.setPen(p)
                    self.painter.drawText(31, 27 + (11 * i), f"{player.username} {player.mods}: {int(player.buffer[-1][1])}, {int(player.buffer[-1][2])}")
                else:
                    self.painter.setPen(p)
                    self.painter.drawText(35, 27 + (11 * i), f"{player.username} {player.mods}: Not yet loaded")
            self.painter.setPen(PEN_WHITE)
            if self.replay_amount == 2:
                try:
                    player = self.players[1]
                    prev_player = self.players[0]
                    distance = math.sqrt(((prev_player.buffer[-1][1] - player.buffer[-1][1]) ** 2) +
                                         ((prev_player.buffer[-1][2] - player.buffer[-1][2]) ** 2))
                    self.painter.drawText(5, 39 + (12 * 1), f"Distance {prev_player.username}-{player.username}: {int(distance)}px")
                except IndexError: # Edge case where we only have data from one cursor
                    pass

    def paint_frametime_graph(self):
        x_offset = SCREEN_WIDTH
        self.painter.setBrush(BRUSH_DARKGRAY)
        self.painter.setOpacity(0.75)
        self.painter.drawRect(SCREEN_WIDTH - 360, SCREEN_HEIGHT - 100, 360, 100)
        self.painter.setBrush(BRUSH_BLANK)
        # line routine, draws 60/30/15 fps lines
        PEN_GRAY.setWidth(1)
        self.painter.setPen(PEN_GRAY)
        self.painter.setOpacity(1)
        ref_path = QPainterPath()
        ref_path.moveTo(SCREEN_WIDTH - 360, SCREEN_HEIGHT - 17)
        ref_path.lineTo(SCREEN_WIDTH,  SCREEN_HEIGHT - 17)
        ref_path.moveTo(SCREEN_WIDTH - 360, SCREEN_HEIGHT - 33)
        ref_path.lineTo(SCREEN_WIDTH, SCREEN_HEIGHT - 33)
        ref_path.moveTo(SCREEN_WIDTH - 360, SCREEN_HEIGHT - 67)
        ref_path.lineTo(SCREEN_WIDTH, SCREEN_HEIGHT - 67)
        self.painter.drawPath(ref_path)
        # draw frame time graph
        PEN_WHITE.setWidth(1)
        self.painter.setPen(PEN_WHITE)
        frame_path = QPainterPath()
        frame_path.moveTo(x_offset, max(SCREEN_HEIGHT - 100, SCREEN_HEIGHT - (self.frame_times[0])))
        for time in self.frame_times:
            x_offset -= 3
            frame_path.lineTo(x_offset, max(SCREEN_HEIGHT - 100, SCREEN_HEIGHT - time))
        self.painter.drawPath(frame_path)
        # draw fps & ms
        ms = self.frame_times[0]
        fps = 1000 / ms
        self.painter.drawText(SCREEN_WIDTH - 360 + 5, SCREEN_HEIGHT - 100 + 12, f"fps:{int(fps)}")
        self.painter.drawText(SCREEN_WIDTH - 360 + 5, SCREEN_HEIGHT - 100 + 22, "{:.2f}ms".format(ms))

    def draw_line(self, alpha, start, end):
        """
        Draws a line using the given painter, pen, and alpha level from Point start to Point end.

        Arguments:
            QPainter painter: The painter.
            Integer alpha: The alpha level from 0.0-1.0 to set the line to.
                           https://doc.qt.io/qt-5/qcolor.html#alpha-blended-drawing
            List start: The X&Y position of the start of the line.
            List end: The X&Y position of the end of the line.
        """

        self.painter.setOpacity(alpha)
        self.painter.drawLine(start[0] + X_OFFSET, start[1] + Y_OFFSET, end[0] + X_OFFSET, end[1] + Y_OFFSET)

    def draw_cross(self, alpha, point):
        """
        Draws a cross.

        Args:
           QPainter painter: The painter.
           Integer alpha: The alpha level from 0.0-1.0 to set the cross to.
           List point: The X&Y position of the cross.
        """
        half_width = WIDTH_CROSS/2
        self.painter.setOpacity(alpha)
        self.painter.drawLine(point[0] + X_OFFSET + half_width, point[1] + Y_OFFSET + half_width,
                              point[0] + X_OFFSET - half_width, point[1] + Y_OFFSET - half_width)
        self.painter.drawLine(point[0] + X_OFFSET - half_width, point[1] + Y_OFFSET + half_width,
                              point[0] + X_OFFSET + half_width, point[1] + Y_OFFSET - half_width)

    def draw_hitobject(self, hitobj):
        """
        Calls corresponding functions to draw a Hitobject.

        Args:
            QPainter painter: The painter.
            Hitobj hitobj: A Hitobject.
        """
        if isinstance(hitobj, Circle):
            self.draw_hitcircle(hitobj)
            self.draw_approachcircle(hitobj)
        if isinstance(hitobj, Slider):
            self.draw_slider(hitobj)
        if isinstance(hitobj, Spinner):
            self.draw_spinner(hitobj)

    def draw_hitcircle(self, hitobj):
        """
        Draws Hitcircle.

        Args:
            QPainter painter: The painter.
            Hitobj hitobj: A Hitobject.
        """
        current_time = self.clock.get_time()
        fade_out = max(0, ((current_time - self.get_hit_time(hitobj)) / self.hitwindow))
        opacity = min(1, ((current_time - (self.get_hit_time(hitobj) - self.preempt)) / self.fade_in))
        opacity = max(0, min(1, opacity-fade_out))
        p = hitobj.position

        PEN_WHITE.setWidth(WIDTH_CIRCLE_BORDER)
        self.painter.setOpacity(opacity)
        self.painter.setPen(PEN_WHITE)
        self.painter.setBrush(BRUSH_GRAY)
        self.painter.drawEllipse(QPointF(p.x + X_OFFSET, p.y + Y_OFFSET), self.hitcircle_radius, self.hitcircle_radius)
        self.painter.setBrush(BRUSH_BLANK)

    def draw_spinner(self, hitobj):
        """
        Draws Spinner.

        Args:
            QPainter painter: The painter.
            Hitobj hitobj: A Hitobject.
        """
        current_time = self.clock.get_time()
        if self.get_hit_endtime(hitobj) - current_time < 0:
            return
        radius = (384 / 2)
        fade_out = max(0, ((current_time - self.get_hit_endtime(hitobj)) / self.hitwindow))
        opacity = min(1, ((current_time - (self.get_hit_time(hitobj) - self.preempt)) / self.fade_in))
        opacity = max(0, min(1, opacity-fade_out))
        scale = min(1, (self.get_hit_endtime(hitobj) - current_time) / (self.get_hit_endtime(hitobj) - self.get_hit_time(hitobj)))
        radius = radius * scale

        PEN_WHITE.setWidth(int(WIDTH_CIRCLE_BORDER / 2))
        self.painter.setPen(PEN_WHITE)
        self.painter.setOpacity(opacity)
        self.painter.drawEllipse(QPointF(512 / 2 + X_OFFSET, 384 / 2 + Y_OFFSET), radius, radius)

    def draw_approachcircle(self, hitobj):
        """
        Draws Approachcircle.

        Args:
            QPainter painter: The painter.
            Hitobj hitobj: A Hitobject.
        """
        current_time = self.clock.get_time()
        if self.get_hit_time(hitobj) - current_time < 0:
            return
        opacity = min(1, ((current_time - (self.get_hit_time(hitobj) - self.preempt)) / self.fade_in))
        opacity = max(0, min(1, opacity))
        scale = max(1, ((self.get_hit_time(hitobj) - current_time) / self.preempt) * 3 + 1)
        p = hitobj.position
        radius = self.hitcircle_radius * scale

        PEN_WHITE.setWidth(int(WIDTH_CIRCLE_BORDER / 2))
        self.painter.setPen(PEN_WHITE)
        self.painter.setOpacity(opacity)
        self.painter.drawEllipse(QPointF(p.x + X_OFFSET, p.y + Y_OFFSET), radius, radius)

    def draw_slider(self, hitobj):
        """
        Draws sliderbody and hitcircle & approachcircle if needed

        Args:
            QPainter painter: The painter.
            Hitobj hitobj: A Hitobject.
        """
        self.draw_sliderbody(hitobj)
        self.draw_hitcircle(hitobj)
        self.draw_approachcircle(hitobj)

    def draw_sliderbody(self, hitobj):
        """
        Draws a sliderbody using a QpainterPath.

        Args:
            QPainter painter: The painter.
            Hitobj hitobj: A Hitobject.
        """
        sliderbody = QPainterPath()
        current_time = self.clock.get_time()
        fade_out = max(0, ((current_time - self.get_hit_endtime(hitobj)) / self.hitwindow))
        opacity = min(1, ((current_time - (self.get_hit_time(hitobj) - self.preempt)) / self.fade_in))
        opacity = max(0, min(1, opacity-fade_out)) * 0.75
        p = hitobj.position

        PEN_GRAY.setWidth(self.hitcircle_radius * 2 + WIDTH_CIRCLE_BORDER)
        PEN_GRAY.setCapStyle(Qt.RoundCap)
        PEN_GRAY.setJoinStyle(Qt.RoundJoin)
        self.painter.setPen(PEN_GRAY)
        self.painter.setOpacity(opacity)

        sliderbody.moveTo(p.x + X_OFFSET, p.y + Y_OFFSET)
        for i in hitobj.slider_body:
            sliderbody.lineTo(i.x + X_OFFSET, i.y + Y_OFFSET)
        self.painter.drawPath(sliderbody)

    def draw_progressbar(self, percentage):
        loading_bg = QPainterPath()
        loading_bar = QPainterPath()
        c = self.painter.pen().color()

        _pen = self.painter.pen()
        _pen.setWidth(5)
        _pen.setCapStyle(Qt.RoundCap)
        _pen.setJoinStyle(Qt.RoundJoin)
        _pen.setColor(QColor(c.red(), c.green(), c.blue(), 25))
        self.painter.setPen(_pen)

        loading_bg.moveTo(SCREEN_WIDTH/2 - 75, SCREEN_HEIGHT / 2)
        loading_bg.lineTo(SCREEN_WIDTH/2 - 75 + 150, SCREEN_HEIGHT / 2)

        loading_bar.moveTo(SCREEN_WIDTH / 2 - 75, SCREEN_HEIGHT / 2)
        loading_bar.lineTo(SCREEN_WIDTH / 2 - 75 + percentage * 1.5, SCREEN_HEIGHT / 2)

        self.painter.drawPath(loading_bg)
        _pen.setColor(QColor(c.red(), c.green(), c.blue(), 255))
        self.painter.setPen(_pen)
        self.painter.drawPath(loading_bar)

    def draw_loading_screen(self):
        self.painter.drawText(SCREEN_WIDTH / 2 - 75, SCREEN_HEIGHT / 2 - 10, f"Calculating Sliders, please wait...")
        self.draw_progressbar(int((self.sliders_current / self.sliders_total) * 100))

    def process_sliders(self):
        self.sliders_total = len(self.beatmap.hit_objects) - 1
        for index in range(len(self.beatmap.hit_objects)):
            self.sliders_current = index
            current_hitobj = self.beatmap.hit_objects[index]
            if isinstance(current_hitobj, Slider):
                steps = max(1, int((self.beatmap.hit_objects[index].end_time - self.beatmap.hit_objects[index].time).total_seconds() * 50)) + 1
                if isinstance(current_hitobj.curve, Bezier):
                    self.beatmap.hit_objects[index].slider_body = current_hitobj.curve.at(np.array([i / steps for i in range(steps)]))
                elif isinstance(current_hitobj.curve, MultiBezier):
                    self.beatmap.hit_objects[index].slider_body = [current_hitobj.curve(i / steps) for i in range(steps)]
                else:
                    self.beatmap.hit_objects[index].slider_body = current_hitobj.curve.points

    def reset(self, end=False):
        """
        Reset Visualization. If end is passed, the function will reset to the end of the map,
        setting the clock to the the max of the cursor data.

        Args:
            Boolean end: Moves everything to the end of the cursor data.
        """
        self.clock.reset()
        if end:
            self.clock.time_counter = self.playback_len
        if self.paused:
            self.clock.pause()

    def search_nearest_frame(self, reverse=False):
        """
        Args:
            Boolean reverse: chooses the search direction
        """
        if not reverse:
            # len(self.data) is the number of replays being visualized
            # self.data[0] is for the first replay, as is self.pos[0]
            # self.pos is a list of current indecies of the replays
            # self.data[0][self.pos[0]] is the current frame we're on
            # so seek to the next frame; self.pos[0] + 1
            next_frame_times = [self.players[x].data[self.players[x].pos + 1][0] for x in range(len(self.players))]
            self.seek_to(min(next_frame_times) - 1)
        else:
            previous_frame_times = [self.players[x].data[self.players[x].pos - 1][0] for x in range(len(self.players))]
            self.seek_to(min(previous_frame_times) - 1)

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

    def get_hit_endtime(self, hitobj):
        return hitobj.end_time.total_seconds() * 1000 if not isinstance(hitobj, Circle) else self.get_hit_time(hitobj)

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
        speed = get_setting("default_speed")
        self.speed_options = get_setting("speed_options")
        self.renderer = _Renderer(replays, beatmap_id, beatmap_path, speed=speed)

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
        self.next_frame_button.clicked.connect(lambda: self.change_frame(reverse=False))

        self.previous_frame_button = QPushButton()
        self.previous_frame_button.setIcon(QIcon(str(resource_path("./resources/frame_back.png"))))
        self.previous_frame_button.setFixedSize(20, 20)
        self.previous_frame_button.setToolTip("Displays previous frame")
        self.previous_frame_button.clicked.connect(lambda: self.change_frame(reverse=True))

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

        self.speed_label = QLabel(str(speed) + "x")
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
        self.update_speed(abs(self.renderer.clock.current_speed))

    def update_slider(self, value):
        self.slider.setValue(value)

    def play_reverse(self):
        self.renderer.resume()
        self.renderer.play_direction = -1
        self.update_speed(abs(self.renderer.clock.current_speed))

    def update_speed(self, speed):
        self.renderer.clock.change_speed(speed * self.renderer.play_direction)

    def change_frame(self, reverse):
        # only change pause state if we're not paused, this way we don't unpause
        # when changing frames
        if not self.renderer.paused:
            self.pause()
        self.renderer.search_nearest_frame(reverse=reverse)

    def pause(self):
        if self.renderer.paused:
            self.pause_button.setIcon(QIcon(str(resource_path("./resources/pause.png"))))
            self.renderer.resume()
        else:
            self.pause_button.setIcon(QIcon(str(resource_path("./resources/play.png"))))
            self.renderer.pause()

    def lower_speed(self):
        index = self.speed_options.index(abs(self.renderer.clock.current_speed))
        if index != 0:
            speed = self.speed_options[index - 1]
            self.speed_label.setText(str(speed) + "x")
            self.update_speed(speed)

    def increase_speed(self):
        index = self.speed_options.index(abs(self.renderer.clock.current_speed))
        if index != len(self.speed_options) - 1:
            speed = self.speed_options[index + 1]
            self.speed_label.setText(str(speed) + "x")
            self.update_speed(speed)


class VisualizerWindow(QMainWindow):
    def __init__(self, replays=[], beatmap_id=None, beatmap_path=None):
        super(VisualizerWindow, self).__init__()
        self.setWindowTitle("Visualizer")
        self.setWindowIcon(QIcon(str(resource_path("resources/logo.ico"))))
        self.interface = _Interface(replays, beatmap_id, beatmap_path)
        self.setCentralWidget(self.interface)
        self.setWindowFlag(Qt.MSWindowsFixedSizeDialogHint) # resizing is not important rn
        QShortcut(QKeySequence(Qt.Key_Space), self, self.interface.pause)
        QShortcut(QKeySequence(Qt.Key_Right), self, lambda: self.interface.change_frame(reverse=False))
        QShortcut(QKeySequence(Qt.Key_Left), self, lambda: self.interface.change_frame(reverse=True))
        QShortcut(QKeySequence(Qt.Key_Up), self, self.interface.increase_speed)
        QShortcut(QKeySequence(Qt.Key_Down), self, self.interface.lower_speed)
        QShortcut(QKeySequence(Qt.CTRL + Qt.Key_F11), self, self.toggle_frametime)

    def closeEvent(self, event):
        super().closeEvent(event)
        self.interface.renderer.timer.stop()
        np.seterr(**PREVIOUS_ERRSTATE)

    def toggle_frametime(self):
        set_setting("visualizer_frametime", not get_setting("visualizer_frametime"))