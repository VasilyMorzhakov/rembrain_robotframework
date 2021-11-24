import os
from multiprocessing import Queue

import pytest
from envyaml import EnvYAML
from pytest_mock import MockerFixture

from rembrain_robot_framework import RobotDispatcher
from rembrain_robot_framework.processes import StubProcess
from rembrain_robot_framework.tests.common.processes import *


# first way
@pytest.fixture()
def robot_dispatcher_fx(request) -> RobotDispatcher:
    config: T.Any = EnvYAML(os.path.join(os.path.dirname(__file__), "configs", request.param[0]))
    robot_dispatcher = RobotDispatcher(config, request.param[1])
    robot_dispatcher.start_processes()

    yield robot_dispatcher

    robot_dispatcher.log_listener.stop()


# second way
@pytest.fixture()
def robot_dispatcher_class_fx(request, mocker: MockerFixture) -> RobotDispatcher:
    config: T.Any = EnvYAML(os.path.join(os.path.dirname(__file__), "configs", request.param[0]))

    def set_logging(self, *args):
        self.log = type("MOCK_LOG", (object,), {"info": lambda x: ..., })

    mocker.patch.object(RobotDispatcher, 'set_logging', set_logging)
    yield RobotDispatcher, config


@pytest.mark.parametrize(
    'robot_dispatcher_fx',
    (("config1.yaml", {
        "p1": {"process_class": P1, "keep_alive": False},
        "p1_new": {"process_class": P1, "keep_alive": False},
        "p2": {"process_class": P2, "keep_alive": False},
        "p2_new": {"process_class": P2, "keep_alive": False},
    }),), indirect=True
)
@pytest.mark.skip
def test_queues_are_the_same(robot_dispatcher_fx: RobotDispatcher) -> None:
    time.sleep(3.0)
    assert robot_dispatcher_fx.shared_objects["hi_received"].value, 4
    assert robot_dispatcher_fx.processes["p2"]["consume_queues"]["messages"]._maxsize == 20


@pytest.mark.parametrize(
    'robot_dispatcher_fx',
    (("config2.yaml", {
        "p1": {"process_class": P1, "keep_alive": False},
        "p1_new": {"process_class": P1, "keep_alive": False},
        "p3": {"process_class": P3, "keep_alive": False},
    }),), indirect=True
)
@pytest.mark.skip
def test_input_queues_different(robot_dispatcher_fx: RobotDispatcher) -> None:
    time.sleep(3.0)
    assert robot_dispatcher_fx.shared_objects["hi_received"].value, 2
    assert robot_dispatcher_fx.processes["p3"]["consume_queues"]["messages1"]._maxsize == 10
    assert robot_dispatcher_fx.processes["p3"]["consume_queues"]["messages2"]._maxsize == 50


@pytest.mark.parametrize(
    'robot_dispatcher_fx',
    (("config3.yaml", {
        "p4": {"process_class": P4, "keep_alive": False},
        "p2": {"process_class": P2, "keep_alive": False, "expect": "hi1"},
        "p2_new": {"process_class": P2, "keep_alive": False},
    }),), indirect=True
)
@pytest.mark.skip
def test_output_queues_different(robot_dispatcher_fx: RobotDispatcher) -> None:
    time.sleep(3.0)
    assert robot_dispatcher_fx.shared_objects["hi_received"].value, 2


@pytest.mark.parametrize(
    'robot_dispatcher_fx',
    (("config4.yaml", {
        "p1": {"process_class": VideoSender, "keep_alive": False},
        "p2": {"process_class": VideoConsumer, "keep_alive": False},
    }),), indirect=True
)
def test_performance(robot_dispatcher_fx: RobotDispatcher) -> None:
    time.sleep(20.0)
    assert robot_dispatcher_fx.shared_objects["ok"].value, 1


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

    robot_dispatcher.log_listener.stop()


@pytest.mark.parametrize(
    'robot_dispatcher_class_fx',
    (("config_empty.yaml", {}), ("config_without_data.yaml", {})),
    indirect=True
)
def test_empty_config(robot_dispatcher_class_fx: tuple):
    class_, config = robot_dispatcher_class_fx
    with pytest.raises(Exception) as exc_info:
        class_(config, {})

    assert "'Config' params  are incorrect. Please, check config file." in str(exc_info.value)
