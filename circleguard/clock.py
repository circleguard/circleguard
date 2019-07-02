import time


class Timer:
    def __init__(self):
        self.time_counter = 0
        self.current_speed = 1
        self.paused = False
        self.paused_at_run_time = None
        self.last_run_time = time.time_ns()

    def get_time(self):
        if not self.paused:
            current_run_time = time.time_ns()
            time_took = current_run_time-self.last_run_time
            self.time_counter += time_took/1000000*self.current_speed
            self.last_run_time = time.time_ns()
        return self.time_counter

    def pause(self):
        self.paused = True
        self.paused_at_run_time = time.time_ns()
        return self.get_time()

    def resume(self):
        self.paused = False
        self.last_run_time += (time.time_ns()-self.paused_at_run_time)
        self.paused_at_run_time = None
        return self.get_time()

    def reset(self):
        self.__init__()
        return self.get_time()

    def change_speed(self, speed):
        self.current_speed = speed
        return self.get_time()
