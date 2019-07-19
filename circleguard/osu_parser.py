import io


class Beatmap():

    def __init__(self, path):

        self.hit_objects = []
        self.position = 0  # index into hit_objects; how many hit objects along we are
        self.current_time = 0  # the time we are in the beatmap; see #advance and #next_time
        self.next_time = 0
        self.last_time = 0

        with io.open(path, mode="r", encoding="utf-8") as f:  # so we can open files with weeb letters c:
            lines = [line.rstrip("\n") for line in f]

        offset = 0
        # find variables. could probably be written better
        for i, line in enumerate(lines[offset:]):
            if "CircleSize" in line:
                self.cs = float(line.split(":")[1])  # CircleSize:4 -> [Circlesize, 4] -> 4
            if "ApproachRate" in line:
                self.ar = float(line.split(":")[1])
            if "HPDrainRate" in line:
                self.hp = float(line.split(":")[1])
            if "OverallDifficulty" in line:
                self.od = float(line.split(":")[1])
            if "SliderMultiplier" in line:
                self.slider_multiplier = float(line.split(":")[1])
            if "SliderTickRate" in line:
                self.slider_multiplier = float(line.split(":")[1])

        for i, line in enumerate(lines[offset:]):
            if "[TimingPoints]" not in line:
                continue
            else:
                offset = offset + i + 1  # the next line is the actual beat duration
                self.beat_duration = float(lines[offset].split(",")[1])

        # find the first line of the hitobjects section
        for i, line in enumerate(lines[offset:]):
            if "[HitObjects]" not in line:
                continue
            else:
                offset = offset + i + 1  # the next line is the actual start of data

        for line in lines[offset:]:
            x, y, time, obj_type = line.split(",")[0:4]
            info = line
            self.hit_objects.append(HitObject(float(x), float(y), float(time), int(obj_type), info, self.slider_multiplier, self.beat_duration))  # passing too many arguments
        self.last_time = self.hit_objects[-1].time+10000  # makes sure last objects are rendered. Doesn't really work with long spinners/sliders, needs to be more complex

        self.next_time = self.hit_objects[0].time  # set next_time properly at the beginning, before we've called #advance

    def advance(self):
        """
        Advances to the next hit object.
        Sets position to the time of the hit object we're advancing to, and sets
        next_time to the time of the hit object after that. Returns the hit object
        we advanced to.
        """

        ret = self.hit_objects[self.position]
        self.position += 1
        self.current_time = ret.time
        try:
            self.next_time = self.hit_objects[self.position].time
        except IndexError:
            self.next_time = 2**64
            self.position -= 1
        return ret

    def reset(self):
        self.position = 0
        self.current_time = 0
        self.next_time = self.hit_objects[0].time


class HitObject:
    def __init__(self, x, y, time, obj_type, info, slider_multiplier, beat_duration):
        """ This function is horrible, needs a complete rewrite"""
        self.x = x
        self.y = y
        types = str(bin(obj_type))[2:]
        self.type = "circle" if int(types[-1]) == 1 else "slider" if int(types[-2]) == 1 else "spinner" if int(types[-4]) == 1 else "Error"
        if self.type == "slider":
            info = info.split("|")
            # I'm sorry :c
            self.slider_mode = info[0].split(",")[-1]
            info.pop(0)
            info = list(filter(lambda a: ":" in a, info))
            info[-1] = info[-1].split(",")
            tmp = info[-1][1:]
            info[-1] = info[-1][0]
            self.slider_info = [[x, y]]
            for obj in info:
                cords = obj.split(":")
                cords = [int(cord) for cord in cords]
                self.slider_info.append(cords)
            self.slider_info.append(cords)
            self.slider_repeats = int(tmp[0])
            self.slider_length = float(tmp[1])
            self.slider_length = self.slider_length / (100.0 * slider_multiplier) * beat_duration
        if self.type == "spinner":
            self.spinner_length = int(info.split(",")[5])
        self.time = time


def from_path(path):
    return Beatmap(path)
