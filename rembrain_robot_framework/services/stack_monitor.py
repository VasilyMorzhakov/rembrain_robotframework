import linecache
import logging
import os
import sys
import time
import threading
import typing as T

logger = logging.getLogger(__name__)


# todo replace to 'services'
class StackMonitor:
    """
    Uses code from the hanging_threads library: https://github.com/niccokunzmann/hanging_threads
    """

    def __init__(self, name, **kwargs):
        """
        :param poll_interval: Interval between stack polls (in seconds) Default: 0.1
        :param print_interval: Interval between stack prints (in seconds) Default: 5
        :param clear_on_print: Whether to clear the stack counters on each print to prevent memory leaks Default: True
        """
        self._monitor_thread: T.Optional[StoppableThread] = None
        self._print_thread: T.Optional[StoppableThread] = None
        self._poll_interval = float(kwargs.get("poll_interval", 0.1))
        self._print_interval = float(kwargs.get("print_interval", 5))
        self._clear_on_print = bool(kwargs.get("clear_on_print", True))
        self._stack_counter = {}
        self._stack_lock = threading.Lock()
        self._interval_start = time.time()
        self._name = name

    def start_monitoring(self):
        self._interval_start = time.time()
        if not self._monitor_thread:
            self._monitor_thread = StoppableThread(target=self._monitor_fn, daemon=True)
            self._monitor_thread.start()
        if not self._print_thread:
            self._print_thread = StoppableThread(target=self._print_stacks, daemon=True)
            self._print_thread.start()

    def _monitor_fn(self):
        while not self._monitor_thread.is_stopped():
            time.sleep(self._poll_interval)
            with self._stack_lock:
                frames = self._get_frames()
                for thread_name in frames:
                    frame_str = frames[thread_name]
                    if thread_name not in self._stack_counter:
                        self._stack_counter[thread_name] = {}
                    if frame_str not in self._stack_counter[thread_name]:
                        self._stack_counter[thread_name][frame_str] = 1
                    else:
                        self._stack_counter[thread_name][frame_str] += 1

    def stop_monitoring(self):
        # Print the stacks one last time
        self.__print()
        with self._stack_lock:
            if self._monitor_thread:
                self._monitor_thread.stop()
            if self._print_thread:
                self._print_thread.stop()

    def _get_frames(self):
        threads = {thread.ident: thread for thread in threading.enumerate()}
        res = {}
        frames = sys._current_frames()
        for thread_id, frame in frames.items():
            if thread_id in (self._monitor_thread.ident, self._print_thread.ident):
                continue
            res[threads[thread_id].name] = self.thread2list(frame)
        return res

    @staticmethod
    def thread2list(frame):
        l = []
        while frame:
            l.insert(0, StackMonitor.frame2string(frame))
            frame = frame.f_back
        return "".join(l)

    @staticmethod
    def frame2string(frame):
        lineno = frame.f_lineno
        co = frame.f_code
        filename = co.co_filename
        name = co.co_name
        s = f"File '{filename}', line {lineno}, in {name}:"
        line = linecache.getline(filename, lineno, frame.f_globals).lstrip()
        return s + f"\r\n\t{line}"

    def _print_stacks(self):
        while True:
            time.sleep(self._print_interval)
            if self._print_thread.is_stopped():
                break
            self.__print()

    def __print(self):
        with self._stack_lock:
            if len(self._stack_counter):
                dt = time.time() - self._interval_start
                res = f"Stack samples for process {os.getpid()}, name {self._name} for the last {dt:.0f} s.:"
                for thread_id, frames_cnt in self._stack_counter.items():
                    res += "\r\n========================================================\r\n"
                    res += f"||THREAD '{thread_id}':||\r\n{self.frame_cnt_to_str(frames_cnt)}"
                # logger.info(res)
                print(res)
                if self._clear_on_print:
                    self._interval_start = time.time()
                    self._stack_counter.clear()

    @staticmethod
    def frame_cnt_to_str(frames_cnt):
        s = ""
        for frame in sorted(frames_cnt, key=frames_cnt.get, reverse=True):
            s += f">>>COUNT: {frames_cnt[frame]}:\r\n{frame}"
        return s


class StoppableThread(threading.Thread):
    def __init__(self, *args, **kwargs):
        super(StoppableThread, self).__init__(*args, **kwargs)
        self._stopped = False

    def stop(self):
        self._stopped = True

    def is_stopped(self):
        return self._stopped


# For debugging of StackMonitor
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    def fn_1():
        print("Hi1")
        time.sleep(1)

    def fn_2():
        print("Hi2")
        time.sleep(0.5)

    def loop():
        while True:
            fn_1()
            fn_2()

    sm = StackMonitor("")
    sm.start_monitoring()

    t1 = threading.Thread(target=loop, daemon=True)
    t1.start()
    time.sleep(5)

    print("\r\nSTOPPED\r\n")
    sm.stop_monitoring()

    time.sleep(20)
