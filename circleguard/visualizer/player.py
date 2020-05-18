class Player():
    def __init__(self, replay, pen):
        self.pen = pen
        self.username = replay.username
        self.t = replay.t
        # copy so we don't flip the actual replay's xy coordinates when we
        # account for hr (not doing this causes replays to be flipped on odd
        # runs of the visualizer and correct on even runs of the visualizer)
        self.xy = replay.xy.copy()
        self.k = replay.k
        self.end_pos = 0
        self.start_pos = 0
        self.mods = replay.mods
