import logging
import os
import time
import typing as T
import unittest
from multiprocessing import Queue

import numpy as np
import yaml

from rembrain_robot_framework import RobotDispatcher, RobotProcess


class P1(RobotProcess):
    def run(self) -> None:
        for i in range(10000):
            if i % 1000 == 0:
                print(i)
            self.shared.state["n_0"] = i
            self.shared.state["status"] = ["ok1", "ok2"][i % 2]
            img = np.random.random((24, 32, 3))
            self.shared.state["img"] = img
            self.shared.state["n_1"] = i
            self.shared.state["n_2"] = str(i)
            self.shared.state["list"] = list(range(9))
            self.shared.started.value = True
        self.shared.finished.value = True
        self.shared.finished_correctly.value += 1


class P2(RobotProcess):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def run(self) -> None:
        while not self.shared.finished.value:
            if not self.shared.started.value:
                continue
            assert(type(self.shared.state["n_0"]) is int)
            assert(type(self.shared.state["n_1"]) is int)
            assert(type(self.shared.state["n_2"]) is str)
            assert(type(self.shared.state["status"]) is str)
            assert(type(self.shared.state["list"]) is list)
            assert(type(self.shared.state["img"]) is np.ndarray)
            assert(len(self.shared.state["list"]) == 9)
            assert(self.shared.state["status"].startswith("ok"))
            assert(self.shared.state["img"].shape == (24, 32, 3))
        self.shared.finished_correctly.value += 1


class TestUnderLoad(unittest.TestCase):
    def test_shared_objects_save_type(self) -> None:
        print("Test: shared objects save type.")
        processes = {
            **{f"p1_{i}": {"process_class": P1, "keep_alive": False} for i in range(5)},
            **{f"p2_{i}": {"process_class": P2, "keep_alive": False} for i in range(5)}}

        with open(os.path.join(os.path.dirname(__file__), "config_load.yaml")) as file:
            config: T.Any = yaml.load(file, Loader=yaml.BaseLoader)
        robot_dispatcher = RobotDispatcher(config, processes)
        robot_dispatcher.start_processes()

        for _ in range(60):
            time.sleep(5)
            if robot_dispatcher.shared_objects["finished"].value:
                break
        time.sleep(5.0)
        self.assertEqual(robot_dispatcher.shared_objects["finished_correctly"].value, 10)


if __name__ == "__main__":
    unittest.main()
