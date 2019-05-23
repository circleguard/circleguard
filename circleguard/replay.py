import numpy as np
import osrparse
from enums import Mod


class Interpolation:
    """A utility class containing coordinate interpolations."""

    @staticmethod
    def linear(x1, x2, r):
        """
        Linearly interpolates coordinate tuples x1 and x2 with ratio r.

        Args:
            Float x1: The startpoint of the interpolation.
            Float x2: The endpoint of the interpolation.
            Float r: The ratio of the points to interpolate to.
        """

        return ((1 - r) * x1[0] + r * x2[0], (1 - r) * x1[1] + r * x2[1])

    @staticmethod
    def before(x1, x2, r):
        """
        Returns the startpoint of the range.

        Args:
            Float x1: The startpoint of the interpolation.
            Float x2: The endpoint of the interpolation.
            Float r: Ignored.
        """

        return x2

class Replay:
    """
    This class represents a replay as its cursor positions and playername.

    Attributes:
        List replay_data: A list of osrpasrse.ReplayEvent objects, containing
                          x, y, time_since_previous_action, and keys_pressed.
        String player_name: The player who set the replay. Often given as a player id.
        Frozenset enabled_mods: A frozen set containing Mod enums, representing which mods were enabled on the replay.
        Integer replay_id: The id of the replay, if the replay was retrieved from online. None if retrieved locally.
    """

    def __init__(self, replay_data, player_name, enabled_mods):
        """
        Initializes a Replay instance.

        Args:
            List replay_data: A list of osrpasrse.ReplayEvent objects, containing
                              x, y, time_since_previous_action, and keys_pressed.
            String player_name: An identifier marking the player that did the replay. Name or user id are common.
            [Frozenset or Integer] enabled_mods: A frozenset containing Mod enums, or base10 representation of
                                                 the enabled mods on the replay.
        """

        self.play_data = replay_data
        self.player_name = player_name

        # we good if it's already a frozenset
        if(type(enabled_mods) is frozenset):
            self.enabled_mods = enabled_mods
            return

        # Else make it one; taken directly from
        # https://github.com/kszlim/osu-replay-parser/blob/master/osrparse/replay.py#L64
        def bits(n):
            if n == 0:
                yield 0
            while n:
                b = n & (~n+1)
                yield b
                n ^= b

        bit_values_gen = bits(enabled_mods)
        self.enabled_mods = frozenset(Mod(mod_val) for mod_val in bit_values_gen)


    @staticmethod
    def interpolate(data1, data2, interpolation=Interpolation.linear, unflip=False):
        """
        Interpolates the longer of the datas to match the timestamps of the shorter.

        Args:
            List data1: A list of tuples of (t, x, y).
            List data2: A list of tuples of (t, x, y).
            Boolean unflip: Preserves input order of data1 and data2 if True.

        Returns:
            If unflip:
                The tuple (data1, data2), where one is interpolated to the other
                and said other without uninterpolatable points.
            Else:
                The tuple (clean, inter), respectively the shortest of
                the datasets without uninterpolatable points and the longest
                interpolated to the timestamps of shortest.

        """

        flipped = False

        # if the first timestamp in data2 is before the first in data1 switch
        # so data1 always has some timestamps before data2.
        if data1[0][0] > data2[0][0]:
            flipped = not flipped
            (data1, data2) = (data2, data1)

        # get the smallest index of the timestamps after the first timestamp in data2.
        i = next((i for (i, p) in enumerate(data1) if p[0] > data2[0][0]))

        # remove all earlier timestamps, if data1 is longer than data2 keep one more
        # so that the longest always starts before the shorter dataset.
        data1 = data1[i:] if len(data1) < len(data2) else data1[i - 1:]

        if len(data1) > len(data2):
            flipped = not flipped
            (data1, data2) = (data2, data1)

        # for each point in data1 interpolate the points around the timestamp in data2.
        j = 0
        inter = []
        clean = []
        for between in data1:
            # keep a clean version with only values that can be interpolated properly.
            clean.append(between)

            # move up to the last timestamp in data2 before the current timestamp.
            while j < len(data2) - 1 and data2[j][0] < between[0]:
                j += 1

            if j == len(data2) - 1:
                break

            before = data2[j]
            after = data2[j + 1]

            # calculate time differences
            # dt1 =  ---2       , data1
            # dt2 = 1-------3   , data2
            dt1 = between[0] - before[0]
            dt2 = after[0] - before[0]

            # skip trying to interpolate to this event
            # if its surrounding events are not set apart in time
            # and replace it with the event before it
            if dt2 == 0:
                inter.append((between[0], *before[1:]))
                continue

            # interpolate the coordinates in data2
            # according to the ratios of the time differences
            x_inter = interpolation(before[1:], after[1:], dt1 / dt2)

            # filter out interpolation artifacts which send outliers even further away
            if abs(x_inter[0]) > 600 or abs(x_inter[1]) > 600:
                inter.append(between)
                continue

            t_inter = between[0]

            inter.append((t_inter, *x_inter))

        if unflip and flipped:
            (clean, inter) = (inter, clean)

        return (clean, inter)

    @staticmethod
    def resample(timestamped, frequency):
        """
        Resample timestamped data at the given frequency.

        Args:
            List timestamped: A list of tuples of (t, x, y).
            Float frequency: The frequency to resample data to in Hz.

        Returns
            A list of tuples of (t, x, y) with constant time interval 1 / frequency.
        """

        i = 0
        t = timestamped[0][0]
        t_max = timestamped[-1][0]

        resampled = []

        while t < t_max:
            while timestamped[i][0] < t:
                i += 1

            dt1 = t - timestamped[i - 1][0]
            dt2 = timestamped[i][0] - timestamped[i - 1][0]

            inter = Interpolation.linear(timestamped[i - 1][1:], timestamped[i][1:], dt1 / dt2)

            resampled.append((t, *inter))
            t += 1000 / frequency

        return resampled

    @staticmethod
    def skip_breaks(timestamped, break_threshold=1000):
        """
        Eliminates pauses and breaks between events
        longer than the specified threshold in ms.

        Args:
            List timestamped: A list of tuples of (t, x, y).
            Integer break_threshold: The smallest pause in events to be recognized as a break.

        Returns:
            A list of tuples of (t, x, y) without breaks.
        """
        total_break_time = 0

        skipped = []
        t_prev = timestamped[0][0]
        for event in timestamped:
            dt = event[0] - t_prev

            if dt > break_threshold:
                total_break_time += dt

            skipped.append((event[0] - total_break_time, *event[1:]))
            t_prev = event[0]

        return skipped

    def as_list_with_timestamps(self):
        """
        Gets the playdata as a list of tuples of absolute time, x and y.

        Returns:
            A list of tuples of (t, x, y).
        """

        # get all offsets sum all offsets before it to get all absolute times
        timestamps = np.array([e.time_since_previous_action for e in self.play_data])
        timestamps = timestamps.cumsum()

        # zip timestamps back to data and convert t, x, y to tuples
        txy = [[z[0], z[1].x, z[1].y] for z in zip(timestamps, self.play_data)]
        # sort to ensure time goes forward as you move through the data
        # in case someone decides to make time go backwards anyway
        txy.sort(key=lambda p: p[0])
        return txy


# fail fast
np.seterr(all='raise')
