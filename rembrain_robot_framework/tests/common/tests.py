import os
from multiprocessing import Queue

from rembrain_robot_framework import RobotDispatcher
from rembrain_robot_framework.tests.common.processes import *
from rembrain_robot_framework.tests.utils import get_config


def test_queues_are_the_same() -> None:
    config: T.Any = get_config(os.path.join(os.path.dirname(__file__), "configs", "config1.yaml"))
    processes = {
        "p1": {"process_class": P1, "keep_alive": False},
        "p1_new": {"process_class": P1, "keep_alive": False},
        "p2": {"process_class": P2, "keep_alive": False},
        "p2_new": {"process_class": P2, "keep_alive": False},
    }

    robot_dispatcher = RobotDispatcher(config, processes)
    robot_dispatcher.start_processes()
    time.sleep(3.0)
    assert robot_dispatcher.shared_objects["hi_received"].value, 4


def test_input_queues_different() -> None:
    config: T.Any = get_config(os.path.join(os.path.dirname(__file__), "configs", "config2.yaml"))
    processes = {
        "p1": {"process_class": P1, "keep_alive": False},
        "p1_new": {"process_class": P1, "keep_alive": False},
        "p3": {"process_class": P3, "keep_alive": False},
    }

    robot_dispatcher = RobotDispatcher(config, processes)
    robot_dispatcher.start_processes()
    time.sleep(3.0)
    assert robot_dispatcher.shared_objects["hi_received"].value, 2


def test_output_queues_different() -> None:
    config: T.Any = get_config(os.path.join(os.path.dirname(__file__), "configs", "config3.yaml"))
    processes = {
        "p4": {"process_class": P4, "keep_alive": False},
        "p2": {"process_class": P2, "keep_alive": False, "expect": "hi1"},
        "p2_new": {"process_class": P2, "keep_alive": False},
    }

    robot_dispatcher = RobotDispatcher(config, processes)
    robot_dispatcher.start_processes()
    time.sleep(3.0)
    assert robot_dispatcher.shared_objects["hi_received"].value, 2


def test_add_custom_processes() -> None:
    name = "aps"
    queue = Queue(maxsize=30)
    test_message = "TEST MESSAGE"

    robot_dispatcher = RobotDispatcher()
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
    assert robot_dispatcher.shared_objects["success"].value, True


def test_performance() -> None:
    config: T.Any = get_config(os.path.join(os.path.dirname(__file__), "configs", "config4.yaml"))
    processes = {
        "p1": {"process_class": VideoSender, "keep_alive": False},
        "p2": {"process_class": VideoConsumer, "keep_alive": False},
    }

    robot_dispatcher = RobotDispatcher(config, processes)
    robot_dispatcher.start_processes()
    time.sleep(20.0)
    assert robot_dispatcher.shared_objects["ok"].value, 1
