import threading
import math

import numpy as np
from circleguard import Mod, Key
from slider import Beatmap, Library
from slider.beatmap import Circle, Slider, Spinner
from slider.mod import circle_radius, od_to_ms
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QPointF, QRectF
from PyQt5.QtWidgets import QWidget, QFrame, QMainWindow, QVBoxLayout, QShortcut, QApplication
from PyQt5.QtGui import QColor, QPainterPath, QPainter, QPen, QKeySequence, QIcon, QPalette, QBrush

from .clock import Timer
from utils import resource_path, Player
from settings import get_setting, set_setting, toggle_setting
from widgets import VisualizerControls
from .runtime_tracker import RunTimeAnalyser


PREVIOUS_ERRSTATE = np.seterr('raise')

WIDTH_LINE = 1
WIDTH_CROSS = 2
WIDTH_CIRCLE_BORDER = 8
LENGTH_CROSS = 6
FRAMES_ON_SCREEN = 15  # how many frames for each replay to draw on screen at a time

PEN_WHITE = QPen(QColor(200, 200, 200))
PEN_GRAY = QPen(QColor(75, 75, 75))
PEN_GREY_INACTIVE = QPen(QColor(133, 125, 125))
PEN_HIGHLIGHT = QPen(QColor(230, 212, 92))
PEN_BLANK = QPen(QColor(0, 0, 0, 0))

BRUSH_WHITE = QBrush(QColor(200, 200, 200))
BRUSH_GRAY = QBrush(QColor(100, 100, 100))
BRUSH_DARKGRAY = QBrush(QColor(10, 10, 10))
BRUSH_BLANK = QBrush(QColor(0, 0, 0, 0))

GAMEPLAY_PADDING_WIDTH = 64 + 192
GAMEPLAY_PADDING_HEIGHT = 48 + 48
GAMEPLAY_WIDTH = 512
GAMEPLAY_HEIGHT = 384

FRAMETIME_STEPS = 3
FRAMETIME_FRAMES = 120
SLIDER_TICKRATE = 50


class Renderer(QFrame):
    update_signal = pyqtSignal(int)
    analyzer = RunTimeAnalyser(frame_buffer=FRAMETIME_FRAMES)

    def __init__(self, beatmap_info, replays, parent=None, events=[], speed=1):
        super().__init__(parent)
        self.setMinimumSize(GAMEPLAY_WIDTH + GAMEPLAY_PADDING_WIDTH*2, GAMEPLAY_HEIGHT + GAMEPLAY_PADDING_HEIGHT*2)

        # list of timestamps to highlight the frames of in a different color
        self.events = events

        self.painter = QPainter()
        self.scale = 1
        self.x_offset = 0
        self.y_offset = 0

        # beatmap init stuff
        self.hitobjs = []


        if beatmap_info.path:
            self.beatmap = Beatmap.from_path(beatmap_info.path)
            self.playback_len = self.get_hit_endtime(self.beatmap.hit_objects[-1])
        elif beatmap_info.map_id:
            self.beatmap = Library(get_setting("cache_dir")).lookup_by_id(beatmap_info.map_id, download=True, save=True)
            self.playback_len = self.get_hit_endtime(self.beatmap.hit_objects[-1])
        else:
            self.playback_len = 0

        self.has_beatmap = beatmap_info.available()
        # TODO inelegant way to handle this, maybe rename some variables at the least
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
            self.sliders_total = len(self.beatmap.hit_objects)
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
                Player(replay=replay,
                       pen=QPen(QColor().fromHslF(replays.index(replay) / self.replay_amount, 0.75, 0.5)),))
        self.playback_len = max(max(player.t) for player in self.players) if self.replay_amount > 0 else self.playback_len
        # flip all replays with hr
        for player in self.players:
            if Mod.HardRock in player.mods:
                for d in player.xy:
                    d[1] = 384 - d[1]

        # clock stuff
        self.clock = Timer(speed)
        self.paused = False
        self.play_direction = 1

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

    def resizeEvent(self, event):
        width = event.size().width() - GAMEPLAY_PADDING_WIDTH * 2
        height = event.size().height() - GAMEPLAY_PADDING_HEIGHT * 2
        y_scale = height / GAMEPLAY_HEIGHT
        x_scale = width / GAMEPLAY_WIDTH
        if GAMEPLAY_WIDTH * y_scale > width:
            self.scale = x_scale
            self.y_offset = (height - GAMEPLAY_HEIGHT * x_scale) / 2
            self.x_offset = 0
        else:
            self.scale = y_scale
            self.y_offset = 0
            self.x_offset = (width - GAMEPLAY_WIDTH * y_scale) / 2

    def _x(self, position):
        return self.x_offset + GAMEPLAY_PADDING_WIDTH + self.scaled_number(position)

    def _y(self, position):
        return self.y_offset + GAMEPLAY_PADDING_HEIGHT + self.scaled_number(position)

    def scaled_point(self, x, y):
        return QPointF(self._x(x), self._y(y))

    def scaled_number(self, n):
        return n * self.scale

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
        # if we're at the end of the track or are at the beginning of the track
        # (and thus are reversing), pause and dont update
        if current_time > self.playback_len or current_time < 0:
            self.pause()
            return

        for player in self.players:
            player.end_pos = np.searchsorted(player.t, current_time, "right") - 1
            player.start_pos = player.end_pos - FRAMES_ON_SCREEN if player.end_pos >= FRAMES_ON_SCREEN else 0

        if self.has_beatmap:
            self.get_hitobjects()
        self.update_signal.emit(current_time)
        self.update()

    @analyzer.track
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
                hit_end = self.get_hit_endtime(current_hitobj) + self.fade_in
            else:
                hit_end = hit_t + self.hitwindow + self.fade_in
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
        show_frametime = get_setting("visualizer_frametime")
        if show_frametime:
            self.analyzer.new_frame()
            self.paint_frametime_graph()
        self.analyzer.toggle(show_frametime)
        self.painter.end()

    @analyzer.track
    def paint_cursor(self, player):
        """
        Draws a cursor.

        Arguments:
            Player player: player to draw the cursor of.
        """
        alpha_step = 1 / FRAMES_ON_SCREEN
        pen = player.pen
        pen.setWidth(self.scaled_number(WIDTH_LINE))
        PEN_HIGHLIGHT.setWidth(self.scaled_number(WIDTH_LINE))
        self.painter.setPen(pen)
        highlighted_pen = False
        for i in range(player.start_pos, player.end_pos):
            highlight = any((player.t[i + 1] in self.events, player.t[i] in self.events))
            if highlight and not highlighted_pen:
                self.painter.setPen(PEN_HIGHLIGHT)
                highlighted_pen = True
            elif not highlight and highlighted_pen:
                self.painter.setPen(pen)
                highlighted_pen = False
            self.draw_line((i-player.start_pos) * alpha_step, (player.xy[i][0], player.xy[i][1]),
                           (player.xy[i + 1][0], player.xy[i + 1][1]))
        pen.setWidth(self.scaled_number(WIDTH_CROSS))
        self.painter.setPen(pen)
        for i in range(player.start_pos, player.end_pos+1):
            alpha = (i - player.start_pos) * alpha_step
            xy = player.xy[i]
            k = player.k[i]
            t = player.t[i]
            highlight = t in self.events
            self.draw_cross(alpha, xy, grey_out = not bool(k), highlight=highlight)
        # reset alpha
        self.painter.setOpacity(1)

    def paint_beatmap(self):
        for hitobj in self.hitobjs[::-1]:
            self.draw_hitobject(hitobj)

    @analyzer.track
    def paint_info(self):
        """
        Draws various Information.

        Args:
           QPainter painter: The painter.
        """
        PEN_WHITE.setWidth(self.scaled_number(1))
        self.painter.setPen(PEN_WHITE)
        self.painter.setOpacity(0.25)
        self.painter.drawRect(QRectF(self.scaled_point(0, 0), self.scaled_point(GAMEPLAY_WIDTH, GAMEPLAY_HEIGHT)))
        PEN_WHITE.setWidth(1)
        self.painter.setPen(PEN_WHITE)
        self.painter.setOpacity(1)
        self.painter.drawText(5, 15, f"Clock: {round(self.clock.get_time())} ms | Cursor count: {len(self.players)}")
        if self.replay_amount > 0:
            for i in range(len(self.players)):
                player = self.players[i]
                pen = player.pen
                self.painter.setPen(PEN_BLANK)
                self.painter.setBrush(QBrush(pen.color()))
                self.painter.setOpacity(1 if Key.M1 in Key(int(player.k[player.end_pos])) else 0.3)
                self.painter.drawRect(5, 27 - 9 + (11 * i), 10, 10)
                self.painter.setOpacity(1 if Key.M2 in Key(int(player.k[player.end_pos])) else 0.3)
                self.painter.drawRect(18, 27 - 9 + (11 * i), 10, 10)
                self.painter.setOpacity(1)
                self.painter.setPen(pen)
                self.painter.drawText(31, 27 + (11 * i), f"{player.username} {player.mods.short_name()}: {int(player.xy[player.end_pos][0])}, {int(player.xy[player.end_pos][1])}")
            self.painter.setPen(PEN_WHITE)
            if self.replay_amount == 2:
                try:
                    player = self.players[1]
                    prev_player = self.players[0]
                    distance = math.sqrt(((prev_player.xy[prev_player.end_pos][0] - player.xy[player.end_pos][0]) ** 2) +
                                         ((prev_player.xy[prev_player.end_pos][1] - player.xy[player.end_pos][1]) ** 2))
                    self.painter.drawText(5, 39 + (12 * 1), f"Distance {prev_player.username}-{player.username}: {int(distance)}px")
                except IndexError: # Edge case where we only have data from one cursor
                    pass

    def paint_frametime_graph(self):
        x_offset = self.width()
        height = self.height()
        width = self.width()
        length = FRAMETIME_FRAMES * FRAMETIME_STEPS
        self.painter.setBrush(BRUSH_DARKGRAY)
        self.painter.setOpacity(0.75)
        self.painter.drawRect(width - length, height - 100, 360, 100)
        self.painter.setBrush(BRUSH_BLANK)
        # line routine, draws 60/30/15 fps lines
        PEN_GRAY.setWidth(1)
        self.painter.setPen(PEN_GRAY)
        self.painter.setOpacity(1)
        ref_path = QPainterPath()
        ref_path.moveTo(width - length, height - 17)
        ref_path.lineTo(width,  height - 17)
        ref_path.moveTo(width - length, height - 33)
        ref_path.lineTo(width, height - 33)
        ref_path.moveTo(width - length, height - 67)
        ref_path.lineTo(width, height - 67)
        self.painter.drawPath(ref_path)
        # draw frame time graph
        PEN_WHITE.setWidth(1)
        self.painter.setPen(PEN_WHITE)
        frame_path = QPainterPath()
        frames = self.analyzer.get_frames()
        frame_path.moveTo(x_offset, max(height - 100, height - frames[0]["total"]))
        for frame in frames:
            x_offset -= FRAMETIME_STEPS
            frame_path.lineTo(x_offset, max(height - 100, height - frame["total"]))
        self.painter.drawPath(frame_path)
        # draw fps & ms
        objects = frames[0]
        ms = frames[0]["total"]
        fps = 1000 / ms
        self.painter.drawText(width - length + 5, height - 100 + 12, f"fps:{int(fps)}")
        self.painter.drawText(width - length + 5, height - 100 + 22, "{:.2f}ms".format(ms))

        for i in range(len(objects)):
            current_key = list(objects.keys())[i]
            self.painter.drawText(width - length/2, height - 100 - 6-10*i, "{}: {:.2f}ms".format(current_key, objects[current_key]))

    def draw_line(self, alpha, start, end):
        """
        Draws a line at the given alpha level from the start point to the end point.

        Arguments:
            Float alpha: The alpha level from 0.0-1.0 to set the line to.
                           https://doc.qt.io/qt-5/qcolor.html#alpha-blended-drawing
            List start: The X&Y position of the start of the line.
            List end: The X&Y position of the end of the line.
        """
        self.painter.setOpacity(alpha)
        self.painter.drawLine(self.scaled_point(start[0], start[1]), self.scaled_point(end[0], end[1]))

    def draw_cross(self, alpha, point, grey_out, highlight):
        """
        Draws a cross.

        Args:
           Float alpha: The alpha level from 0.0-1.0 to set the cross to.
           List point: The X&Y position of the cross.
           Boolean grey_out: Whether to grey out the cross or not.
           Boolean highlight: Whether to highlight the cross or not. This takes
               precedence over ``grey_out`` if both are set.
        """
        prev_pen = None
        if highlight:
            prev_pen = self.painter.pen()
            PEN_HIGHLIGHT.setWidth(self.scaled_number(WIDTH_CROSS))
            self.painter.setPen(PEN_HIGHLIGHT)
        elif grey_out:
            prev_pen = self.painter.pen()
            PEN_GREY_INACTIVE.setWidth(self.scaled_number(WIDTH_CROSS))
            self.painter.setPen(PEN_GREY_INACTIVE)
        half_width = LENGTH_CROSS/2
        x = point[0]
        y = point[1]
        x1 = x + half_width
        x2 = x - half_width
        y1 = y + half_width
        y2 = y - half_width

        self.draw_line(alpha, [x1, y1], [x2, y2])
        self.draw_line(alpha, [x2, y1], [x1, y2])
        if grey_out or highlight:
            self.painter.setPen(prev_pen)


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

    @analyzer.track
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

        PEN_WHITE.setWidth(self.scaled_number(WIDTH_CIRCLE_BORDER))
        self.painter.setOpacity(opacity)
        self.painter.setPen(PEN_WHITE)
        self.painter.setBrush(BRUSH_GRAY)
        self.painter.drawEllipse(self.scaled_point(p.x, p.y), self.scaled_number(self.hitcircle_radius), self.scaled_number(self.hitcircle_radius))
        self.painter.setBrush(BRUSH_BLANK)

    @analyzer.track
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
        radius = GAMEPLAY_HEIGHT / 2
        fade_out = max(0, ((current_time - self.get_hit_endtime(hitobj)) / self.hitwindow))
        opacity = min(1, ((current_time - (self.get_hit_time(hitobj) - self.preempt)) / self.fade_in))
        opacity = max(0, min(1, opacity-fade_out))
        scale = min(1, (self.get_hit_endtime(hitobj) - current_time) / (self.get_hit_endtime(hitobj) - self.get_hit_time(hitobj)))
        radius = radius * scale

        PEN_WHITE.setWidth(self.scaled_number(WIDTH_CIRCLE_BORDER / 2))
        self.painter.setPen(PEN_WHITE)
        self.painter.setOpacity(opacity)
        self.painter.drawEllipse(self.scaled_point(GAMEPLAY_WIDTH / 2, GAMEPLAY_HEIGHT / 2), self.scaled_number(radius), self.scaled_number(radius))

    @analyzer.track
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

        PEN_WHITE.setWidth(self.scaled_number(WIDTH_CIRCLE_BORDER / 2))
        self.painter.setPen(PEN_WHITE)
        self.painter.setOpacity(opacity)
        self.painter.drawEllipse(self.scaled_point(p.x, p.y), self.scaled_number(radius), self.scaled_number(radius))

    @analyzer.track
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

        PEN_GRAY.setWidth(self.scaled_number(self.hitcircle_radius * 2 + WIDTH_CIRCLE_BORDER))
        PEN_GRAY.setCapStyle(Qt.RoundCap)
        PEN_GRAY.setJoinStyle(Qt.RoundJoin)
        self.painter.setPen(PEN_GRAY)
        self.painter.setOpacity(opacity)

        sliderbody.moveTo(self.scaled_point(p.x, p.y))
        for i in hitobj.slider_body:
            sliderbody.lineTo(self.scaled_point(i.x, i.y))
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

        loading_bg.moveTo(self.width()/2 - 75, self.height() / 2)
        loading_bg.lineTo(self.width()/2 - 75 + 150, self.height() / 2)

        loading_bar.moveTo(self.width() / 2 - 75, self.height() / 2)
        loading_bar.lineTo(self.width() / 2 - 75 + percentage * 1.5, self.height() / 2)

        self.painter.drawPath(loading_bg)
        _pen.setColor(QColor(c.red(), c.green(), c.blue(), 255))
        self.painter.setPen(_pen)
        self.painter.drawPath(loading_bar)

    def draw_loading_screen(self):
        self.painter.drawText(self.width() / 2 - 75, self.height() / 2 - 10, f"Calculating Sliders, please wait...")
        self.draw_progressbar(int((self.sliders_current / self.sliders_total) * 100))

    def process_sliders(self):
        for i, hitobj in enumerate(self.beatmap.hit_objects):
            self.sliders_current = i
            if isinstance(hitobj, Slider):
                steps = max(2, int((self.get_hit_endtime(hitobj) - self.get_hit_time(hitobj))/SLIDER_TICKRATE))
                hitobj.slider_body = [hitobj.curve(i / steps) for i in range(steps + 1)]

    def search_nearest_frame(self, reverse=False):
        """
        Args:
            Boolean reverse: chooses the search direction
        """
        if not reverse:
            next_frames = []
            for player in self.players:
                pos = player.end_pos + 1
                # stay at the end of the replay, avoid index error
                if pos == len(player.xy):
                    pos -= 1
                next_frames.append(player.t[pos])
            self.seek_to(min(next_frames))
        else:
            prev_frames = []
            for player in self.players:
                pos = player.end_pos - 1
                # stay at the beginning of the replay, don't wrap around to end
                if pos == -1:
                    pos += 1
                prev_frames.append(player.t[pos])
            self.seek_to(max(prev_frames))

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


class Interface(QWidget):
    def __init__(self, beatmap_info, replays, events=[]):
        super().__init__()
        self.speed_options = get_setting("speed_options")

        speed = get_setting("default_speed")
        self.renderer = Renderer(beatmap_info, replays, speed=speed, events=events)
        self.renderer.update_signal.connect(self.update_slider)

        self.controls = VisualizerControls(speed)
        self.controls.pause_button.clicked.connect(self.pause)
        self.controls.play_reverse_button.clicked.connect(self.play_reverse)
        self.controls.play_normal_button.clicked.connect(self.play_normal)
        self.controls.next_frame_button.clicked.connect(lambda: self.change_frame(reverse=False))
        self.controls.previous_frame_button.clicked.connect(lambda: self.change_frame(reverse=True))
        self.controls.speed_up_button.clicked.connect(self.increase_speed)
        self.controls.speed_down_button.clicked.connect(self.lower_speed)
        self.controls.slider.sliderMoved.connect(self.renderer.seek_to)
        self.controls.slider.setRange(0, self.renderer.playback_len)

        self.layout = QVBoxLayout()
        self.layout.addWidget(self.renderer)
        self.layout.addWidget(self.controls)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.layout)

    def play_normal(self):
        self.renderer.resume()
        self.controls.set_paused_state(False)
        self.renderer.play_direction = 1
        self.update_speed(abs(self.renderer.clock.current_speed))

    def update_slider(self, value):
        self.controls.slider.setValue(value)

    def play_reverse(self):
        self.renderer.resume()
        self.controls.set_paused_state(False)
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
            self.controls.set_paused_state(False)
            self.renderer.resume()
        else:
            self.controls.set_paused_state(True)
            self.renderer.pause()

    def lower_speed(self):
        index = self.speed_options.index(abs(self.renderer.clock.current_speed))
        if index == 0:
            return
        speed = self.speed_options[index - 1]
        self.controls.speed_label.setText(str(speed) + "x")
        self.update_speed(speed)

    def increase_speed(self):
        index = self.speed_options.index(abs(self.renderer.clock.current_speed))
        if index == len(self.speed_options) - 1:
            return
        speed = self.speed_options[index + 1]
        self.controls.speed_label.setText(str(speed) + "x")
        self.update_speed(speed)


class VisualizerWindow(QMainWindow):
    def __init__(self, beatmap_info, replays=[], events=[]):
        super().__init__()

        self.setAutoFillBackground(True)
        self.setWindowTitle("Visualizer")
        self.setWindowIcon(QIcon(resource_path("logo/logo.ico")))
        self.interface = Interface(beatmap_info, replays, events=events)
        self.setCentralWidget(self.interface)

        QShortcut(QKeySequence(Qt.Key_Space), self, self.interface.pause)
        QShortcut(QKeySequence(Qt.Key_Right), self, lambda: self.interface.change_frame(reverse=False))
        QShortcut(QKeySequence(Qt.Key_Left), self, lambda: self.interface.change_frame(reverse=True))
        QShortcut(QKeySequence(Qt.CTRL + Qt.Key_Right), self, self.interface.play_normal)
        QShortcut(QKeySequence(Qt.CTRL + Qt.Key_Left), self, self.interface.play_reverse)
        QShortcut(QKeySequence(Qt.Key_Up), self, self.interface.increase_speed)
        QShortcut(QKeySequence(Qt.Key_Down), self, self.interface.lower_speed)
        QShortcut(QKeySequence(Qt.CTRL + Qt.Key_F11), self, lambda: toggle_setting("visualizer_frametime"))
        QShortcut(QKeySequence.FullScreen, self, self.toggle_fullscreen)
        QShortcut(QKeySequence(Qt.Key_F), self, self.toggle_fullscreen)
        QShortcut(QKeySequence(Qt.ALT + Qt.Key_Return), self, self.toggle_fullscreen)
        QShortcut(QKeySequence(Qt.Key_Escape), self, self.exit_fullscreen)
        QShortcut(QKeySequence.Paste, self, self.seek_to_paste_contents)

    def closeEvent(self, event):
        super().closeEvent(event)
        self.interface.renderer.timer.stop()
        np.seterr(**PREVIOUS_ERRSTATE)

    def toggle_fullscreen(self):
        if self.windowState() == Qt.WindowFullScreen:
            self.exit_fullscreen()
            return
        else:
            self.setWindowState(Qt.WindowFullScreen)

    def exit_fullscreen(self):
        self.setWindowState(Qt.WindowNoState)

    def seek_to_paste_contents(self):
        clipboard = QApplication.clipboard()
        time = clipboard.text()
        try:
            # need float to convert x.0 values, then int to make it an int after
            # (seek_to needs a ms value as an int)
            time = int(float(time))
        except ValueError:
            # invalid time, don't seek
            return
        self.interface.renderer.seek_to(time)
