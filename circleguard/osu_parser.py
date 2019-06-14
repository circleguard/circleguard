
class Beatmap():

    def __init__(self, path):

        self.hit_objects = []
        self.position = 0 # index into hit_objects; how many hit objects along we are
        self.current_time = 0 # the time we are in the beatmap; see #advance and #next_time
        self.next_time = 0

        with open(path) as f:
            lines = [line.rstrip("\n") for line in f]

        offset = 0
        # find the circle size
        for i, line in enumerate(lines[offset:]):
            if("CircleSize" not in line):
                continue
            else:
                self.cs = int(line.split(":")[1]) # CircleSize:4 -> [Circlesize, 4] -> 4

        # find the first line of the hitobjects section
        for i, line in enumerate(lines[offset:]):
            if("[HitObjects]" not in line):
                continue
            else:
                offset = offset + i + 1 # the next line is the actual start of data
        for line in lines[offset:]:
            x, y, time = line.split(",")[0:3]
            self.hit_objects.append(HitObject(float(x), float(y), float(time)))

        self.next_time = self.hit_objects[0].time # set next_time properly at the beginning, before we've called #advance

    def advance(self):
        """
        Advances to the next hit object.
        Sets position to the time of the hit object we're advancing to, and sets
        next_time to the time of the hit object after that. Returns the hit object
        we advanced to.
        """

        ret = self.hit_objects[self.position]
        self.position += 1
        self.current = ret.time
        self.next_time = self.hit_objects[self.position].time

        return ret




class HitObject():

    def __init__(self, x, y, time):
        self.x = x
        self.y = y
        self.time = time

def from_path(path):
    return Beatmap(path)
