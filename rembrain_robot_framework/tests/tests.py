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
        self.publish("hi")

        logging.info(self.name + " hi sent")


class P2(RobotProcess):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.to_expect = kwargs.get("expect", "hi")

    def run(self) -> None:
        start_time: float = time.time()

        while time.time() - start_time < 2:
            record: str = self.consume()
            if record == self.to_expect:
                self.shared.hi_received.value += 1
                logging.info(f"{self.name} {record} received")


class P3(RobotProcess):
    def run(self) -> None:
        rec: str = self.consume("messages1")
        if rec == "hi":
            self.shared.hi_received.value += 1
            logging.info(self.name + " hi received")

        rec = self.consume("messages2")
        if rec == "hi":
            self.shared.hi_received.value += 1
            logging.info(self.name + " hi received")


class P4(RobotProcess):
    def run(self) -> None:
        self.publish(queue_name="messages1", message="hi1")
        self.publish(queue_name="messages2", message="hi2")
        logging.info(self.name + " hi sent")


class AP1(RobotProcess):
    def __init__(self, *args, **kwargs):
        super(AP1, self).__init__(*args, **kwargs)
        self.custom_queue_name = kwargs.get("custom_queue_name")
        self.custom_test_message = kwargs.get("custom_test_message")

    def run(self) -> None:
        self.publish(queue_name=self.custom_queue_name, message=self.custom_test_message)
        logging.info(self.name + " published message successfully.")


class AP2(RobotProcess):
    def __init__(self, *args, **kwargs):
        super(AP2, self).__init__(*args, **kwargs)
        self.custom_queue_name = kwargs.get("custom_queue_name")
        self.custom_test_message = kwargs.get("custom_test_message")

    def run(self) -> None:
        message: T.Any = self.consume(queue_name=self.custom_queue_name)
        logging.info(f"{self.name} get message: {message}")
        self.shared.success.value = message == self.custom_test_message


class VideoSender(RobotProcess):
    def run(self) -> None:
        z = np.zeros((212, 256, 3))
        for _ in range(4000):
            z[:] = np.random.random((212, 256, 3))
            self.publish(z)


class VideoConsumer(RobotProcess):
    def run(self) -> None:
        for _ in range(4000):
            record: str = self.consume()
            assert record.shape == (212, 256, 3)

        self.shared.ok.value = 1


class TestServer(unittest.TestCase):
    def test_queues_are_the_same(self) -> None:
        print("Test: queues are the same.")
        processes = {
            "p1": {"process_class": P1, "keep_alive": False},
            "p1_new": {"process_class": P1, "keep_alive": False},
            "p2": {"process_class": P2, "keep_alive": False},
            "p2_new": {"process_class": P2, "keep_alive": False},
        }

        with open(os.path.join(os.path.dirname(__file__), "config1.yaml")) as file:
            config: T.Any = yaml.load(file, Loader=yaml.BaseLoader)
            robot_dispatcher = RobotDispatcher(config, processes)
            robot_dispatcher.start_processes()

            time.sleep(3.0)
            self.assertEqual(robot_dispatcher.shared_objects["hi_received"].value, 4)

    def test_input_queues_different(self):
        print(f"Test: check queues are different.")
        processes = {
            "p1": {"process_class": P1, "keep_alive": False},
            "p1_new": {"process_class": P1, "keep_alive": False},
            "p3": {"process_class": P3, "keep_alive": False},
        }

        with open(os.path.join(os.path.dirname(__file__), "config2.yaml")) as file:
            config: T.Any = yaml.load(file, Loader=yaml.BaseLoader)

        robot_dispatcher = RobotDispatcher(config, processes)
        robot_dispatcher.start_processes()
        time.sleep(3.0)
        self.assertEqual(robot_dispatcher.shared_objects["hi_received"].value, 2)

    def test_output_queues_different(self) -> None:
        print(f"Test: check output queues are different.")
        processes = {
            "p4": {"process_class": P4, "keep_alive": False},
            "p2": {"process_class": P2, "keep_alive": False, "expect": "hi1"},
            "p2_new": {"process_class": P2, "keep_alive": False},
        }

        with open(os.path.join(os.path.dirname(__file__), "config3.yaml")) as file:
            config: T.Any = yaml.load(file, Loader=yaml.BaseLoader)

        robot_dispatcher = RobotDispatcher(config, processes)
        robot_dispatcher.start_processes()

        time.sleep(3.0)

        self.assertEqual(robot_dispatcher.shared_objects["hi_received"].value, 2)

    def test_add_custom_processes(self):
        name = "aps"
        queue = Queue(maxsize=1000)
        test_message = "TEST MESSAGE"

        robot_dispatcher = RobotDispatcher(project_description={})

        robot_dispatcher.add_shared_object("success", "Value:bool")

        robot_dispatcher.add_process(
            "ap1",
            AP1,
            publish_queues={name: [queue]},
            keep_alive=False,
            custom_queue_name=name,
            custom_test_message=test_message,
        )
        robot_dispatcher.add_process(
            "ap2",
            AP2,
            consume_queues={name: queue},
            keep_alive=False,
            custom_queue_name=name,
            custom_test_message=test_message,
        )

        time.sleep(3.0)
        self.assertEqual(robot_dispatcher.shared_objects["success"].value, True)

    def test_performance(self) -> None:
        print("Test: queues are the same.")
        processes = {
            "p1": {"process_class": VideoSender, "keep_alive": False},
            "p2": {"process_class": VideoConsumer, "keep_alive": False},
        }

        with open(os.path.join(os.path.dirname(__file__), "config4.yaml")) as file:
            config: T.Any = yaml.load(file, Loader=yaml.BaseLoader)

        robot_dispatcher = RobotDispatcher(config, processes)
        robot_dispatcher.start_processes()

        time.sleep(20.0)
        self.assertEqual(robot_dispatcher.shared_objects["ok"].value, 1)


if __name__ == "__main__":
    unittest.main()
