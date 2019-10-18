import time


class Timer:
    def __init__(self):
        self.time_counter = 0
        self.current_speed = 1
        self.paused = False
        self.paused_at_run_time = None
        self.last_run_time = time.perf_counter()

    def get_time(self):
        current_run_time = time.perf_counter()
        if not self.paused:
            time_took = current_run_time-self.last_run_time
            self.time_counter += (time_took*1000)*self.current_speed
            self.last_run_time = current_run_time
        return self.time_counter

    def pause(self):
        current_run_time = time.perf_counter()
        if not self.paused:
            self.paused = True
            self.paused_at_run_time = current_run_time
        return self.get_time()

    def resume(self):
        current_run_time = time.perf_counter()
        if self.paused:
            self.last_run_time += (current_run_time-self.paused_at_run_time)
            self.paused_at_run_time = None
            self.paused = False
        return self.get_time()

    def reset(self):
        self.time_counter = 0
        self.paused = False
        self.paused_at_run_time = None
        self.last_run_time = time.time_ns()
        return self.get_time()

    def change_speed(self, speed):
        self.current_speed = speed
        return self.get_time()
