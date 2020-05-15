from .clock import Timer


class RunTimeAnalyser:
    def __init__(self, frame_buffer=120):
        self._data = []
        self.frame_buffer = frame_buffer
        self._temp_data = {}
        self._frame_time_timer = Timer(1)
        self.enabled = True

    def _add_to_entry(self, t, name="undefined"):
        if name not in self._temp_data.keys():
            self._temp_data[name] = t
        else:
            self._temp_data[name] += t

    def track(self, func):
        def function_wrapper(x, *args, **kwargs):
            if not self.enabled:
                return func(x, *args, **kwargs)
            timer = Timer(1)
            result = func(x, *args, **kwargs)
            self._add_to_entry(timer.get_time(), name=func.__name__)
            return result
        return function_wrapper

    def new_frame(self):
        self._add_to_entry(self._frame_time_timer.get_time(), "total")
        self._data.insert(0, self._temp_data)
        self._data = self._data[:self.frame_buffer]
        self._temp_data = {}
        self._frame_time_timer.reset()

    def get_frames(self):
        return self._data

    def toggle(self, state):
        self.enabled = state
