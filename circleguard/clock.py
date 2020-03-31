import time


class Timer:
    def __init__(self, speed):
        self.time_counter = 0
        self.current_speed = speed
        self.paused = False
        self.paused_at_run_time = None
        self.last_run_time = time.perf_counter_ns()

    def get_time(self):
        if not self.paused:
            current_run_time = time.perf_counter_ns()
            time_took = current_run_time - self.last_run_time
            self.time_counter += time_took / 10 ** 6 * self.current_speed
            self.last_run_time = current_run_time
        return self.time_counter

    def pause(self):
        if not self.paused:
            self.paused = True
            self.paused_at_run_time = time.perf_counter_ns()
        return self.get_time()

    def resume(self):
        if self.paused:
            self.last_run_time += time.perf_counter_ns() - self.paused_at_run_time
            self.paused_at_run_time = None
            self.paused = False
        return self.get_time()

    def reset(self):
        self.time_counter = 0
        self.paused = False
        self.paused_at_run_time = None
        self.last_run_time = time.perf_counter_ns()
        return self.get_time()

    def change_speed(self, speed):
        self.current_speed = speed
        return self.get_time()
