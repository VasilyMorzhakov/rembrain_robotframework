import os
from unittest import mock

import pytest
from envyaml import EnvYAML
from pytest_mock import MockerFixture

from rembrain_robot_framework import RobotDispatcher
from rembrain_robot_framework.processes import StubProcess
from rembrain_robot_framework.tests.common.processes import *


@pytest.fixture()
def robot_dispatcher_fx(request) -> RobotDispatcher:
    config: T.Any = EnvYAML(os.path.join(os.path.dirname(__file__), "configs", request.param[0]))
    robot_dispatcher = RobotDispatcher(config, request.param[1])
    robot_dispatcher.start_processes()

    yield robot_dispatcher

    robot_dispatcher.stop_logging()


# second way
@pytest.fixture()
def robot_dispatcher_class_fx(request, mocker: MockerFixture) -> RobotDispatcher:
    config: T.Any = EnvYAML(os.path.join(os.path.dirname(__file__), "configs", request.param[0]))

    def run_logging(self, *args):
        self.log = type("MOCK_LOG", (object,), {"info": lambda x: ..., })

    mocker.patch.object(RobotDispatcher, "run_logging", run_logging)

    yield RobotDispatcher, config


@pytest.mark.parametrize(
    "robot_dispatcher_fx",
    ((
             "config1.yaml",
             {
                 "p1": {"process_class": P1, "keep_alive": False},
                 "p1_new": {"process_class": P1, "keep_alive": False},
                 "p2": {"process_class": P2, "keep_alive": False},
                 "p2_new": {"process_class": P2, "keep_alive": False},
             },
     ),),
    indirect=True,
)
def test_queues_are_the_same(robot_dispatcher_fx: RobotDispatcher) -> None:
    time.sleep(3.0)
    assert robot_dispatcher_fx.shared_objects["hi_received"].value == 4
    assert robot_dispatcher_fx.get_queue_max_size("messages") == 20


@pytest.mark.parametrize(
    "robot_dispatcher_fx",
    ((
             "config2.yaml",
             {
                 "p1": {"process_class": P1, "keep_alive": False},
                 "p1_new": {"process_class": P1, "keep_alive": False},
                 "p3": {"process_class": P3, "keep_alive": False},
             },
     ),),
    indirect=True,
)
def test_input_queues_different(robot_dispatcher_fx: RobotDispatcher) -> None:
    time.sleep(3.0)
    assert robot_dispatcher_fx.shared_objects["hi_received"].value, 2
    assert robot_dispatcher_fx.get_queue_max_size("messages1") == 10
    assert robot_dispatcher_fx.get_queue_max_size("messages2") == 50


@pytest.mark.parametrize(
    "robot_dispatcher_fx",
    ((
             "config3.yaml",
             {
                 "p4": {"process_class": P4, "keep_alive": False},
                 "p2": {"process_class": P2, "keep_alive": False, "expect": "hi1"},
                 "p2_new": {"process_class": P2, "keep_alive": False},
             },
     ),),
    indirect=True,
)
def test_output_queues_different(robot_dispatcher_fx: RobotDispatcher) -> None:
    time.sleep(3.0)
    assert robot_dispatcher_fx.shared_objects["hi_received"].value == 2


@pytest.mark.parametrize(
    "robot_dispatcher_fx",
    ((
             "config4.yaml",
             {
                 "p1": {"process_class": VideoSender, "keep_alive": False},
                 "p2": {"process_class": VideoConsumer, "keep_alive": False},
             },
     ),),
    indirect=True,
)
def test_performance(robot_dispatcher_fx: RobotDispatcher) -> None:
    time.sleep(20.0)
    assert robot_dispatcher_fx.shared_objects["frames_processed"].value == 4000


@pytest.mark.parametrize(
    "robot_dispatcher_class_fx",
    (("config_empty.yaml",),),
    indirect=True,
)
def test_add_custom_processes(robot_dispatcher_class_fx: tuple) -> None:
    name = "aps"
    test_message = "TEST MESSAGE"

    robot_dispatcher = robot_dispatcher_class_fx[0]()
    queue = robot_dispatcher.manager.Queue(maxsize=30)

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
    assert robot_dispatcher.shared_objects["success"].value


@pytest.mark.parametrize(
    "robot_dispatcher_class_fx",
    (("config_empty.yaml",), ("config_without_data.yaml",)),
    indirect=True,
)
def test_empty_config(robot_dispatcher_class_fx: tuple):
    class_, config = robot_dispatcher_class_fx
    with pytest.raises(Exception) as exc_info:
        class_(config, {})

    assert "'Config' params are incorrect. Please, check config file." in str(exc_info.value)


@pytest.mark.parametrize(
    "robot_dispatcher_fx",
    ((
             "config_with_system_queues.yaml",
             {
                 "sys_p1": {"process_class": SysP1, "keep_alive": False},
                 "sys_p2": {"process_class": SysP2, "keep_alive": False},
             },
     ),),
    indirect=True,
)
def test_system_queue(robot_dispatcher_fx: RobotDispatcher) -> None:
    time.sleep(5.0)

    request: dict = robot_dispatcher_fx.shared_objects["request"]
    response: dict = robot_dispatcher_fx.shared_objects["response"]

    assert request["id"] == response["id"]
    assert request["data"] == SysP1.TEST_MESSAGE
    assert response["data"] == SysP2.TEST_MESSAGE


def test_description_from_config() -> None:
    robot_name = "test_description_robot"

    with mock.patch.dict("os.environ", {"ROBOT_NAME": robot_name}):
        config: T.Any = EnvYAML(os.path.join(os.path.dirname(__file__), "configs", "config_with_description.yaml"))
        rd = RobotDispatcher(config, {"p1": {"process_class": StubProcess, "keep_alive": False}})

        assert all((i in ("subsystem", "robot") for i in rd.project_description))
        assert rd.project_description["subsystem"] == "test_subsystem"
        assert rd.project_description["robot"] == robot_name


@pytest.mark.parametrize(
    "robot_dispatcher_fx",
    ((
             "config_with_queue_sizes.yaml",
             {
                 "p1": {"process_class": QueueSizeP1, "keep_alive": False},
                 "p2": {"process_class": QueueSizeP2, "keep_alive": False},
             },
     ),),
    indirect=True,
)
def test_check_overflow(mocker: MockerFixture, robot_dispatcher_fx: RobotDispatcher) -> None:
    warn_message = ""

    def _warning(*args):
        nonlocal warn_message
        warn_message = args[0]

    mocker.patch.object(robot_dispatcher_fx.log, "warning", _warning)

    assert not robot_dispatcher_fx.check_queues_overflow()
    assert not warn_message

    shared = robot_dispatcher_fx.shared_objects

    # 1 from 2
    shared["publish_message"]["repeats"] = 1
    shared["publish_message"]["queue_name"] = "messages1"
    time.sleep(3)
    assert not robot_dispatcher_fx.check_queues_overflow()

    # 2 from 2
    shared["publish_message"]["repeats"] = 1
    shared["publish_message"]["queue_name"] = "messages1"
    time.sleep(2)
    assert robot_dispatcher_fx.check_queues_overflow()
    assert (warn_message == "Consume queue messages1 of process p2 has reached 2 messages.")

    # 2 from 3
    # firstly clean first queue
    warn_message = ""
    shared["consume_message"]["repeats"] = 2
    shared["consume_message"]["queue_name"] = "messages1"
    shared["publish_message"]["repeats"] = 2
    shared["publish_message"]["queue_name"] = "messages2"
    time.sleep(2)
    assert not robot_dispatcher_fx.check_queues_overflow()
    assert not warn_message

    # 9 from 10
    shared["publish_message"]["repeats"] = 9
    shared["publish_message"]["queue_name"] = "messages4"
    time.sleep(2)
    assert robot_dispatcher_fx.check_queues_overflow()
    assert (warn_message == "Consume queue messages4 of process p2 has reached 9 messages.")

    warn_message = ""
    shared["consume_message"]["repeats"] = 1
    shared["consume_message"]["queue_name"] = "messages4"
    time.sleep(2)
    assert not robot_dispatcher_fx.check_queues_overflow()
    assert not warn_message

    # 3 from 4
    shared["publish_message"]["repeats"] = 3
    shared["publish_message"]["queue_name"] = "messages3"
    time.sleep(2)
    assert not robot_dispatcher_fx.check_queues_overflow()
    assert not warn_message

    # 4 from 4
    shared["publish_message"]["repeats"] = 1
    shared["publish_message"]["queue_name"] = "messages3"
    time.sleep(2)
    assert robot_dispatcher_fx.check_queues_overflow()
    assert (warn_message == "Consume queue messages3 of process p2 has reached 4 messages.")

    shared["finish_load"].value = True

    warn_message = ""
    shared["consume_message"]["repeats"] = 2
    shared["consume_message"]["queue_name"] = "messages2"
    time.sleep(2)
    assert robot_dispatcher_fx.check_queues_overflow()  # "messages3" stayed full
    assert (warn_message == "Consume queue messages3 of process p2 has reached 4 messages.")

    warn_message = ""
    shared["consume_message"]["repeats"] = 1
    shared["consume_message"]["queue_name"] = "messages3"
    time.sleep(2)
    assert (not robot_dispatcher_fx.check_queues_overflow())  # "messages3" consisted of 3 from 4
    assert not warn_message

    shared["finish_dump"].value = True
    time.sleep(2)


@pytest.mark.parametrize(
    "robot_dispatcher_fx",
    ((
             "config_full.yaml",
             {
                 "p1": {"process_class": StubProcess, "keep_alive": False},
                 "p2": {"process_class": StubProcess, "keep_alive": False},
             },
     ),),
    indirect=True,
)
def test_correct_dispatcher_full_creation(robot_dispatcher_fx: RobotDispatcher) -> None:
    assert "subsystem" in robot_dispatcher_fx.project_description
    assert robot_dispatcher_fx.project_description["subsystem"] == "TEST"

    assert robot_dispatcher_fx._max_queue_sizes
    mqs = {"messages1": 5, "messages2": 10, "messages3": 50, "messages4": 50}
    assert all(k in mqs and mqs[k] == v for k, v in robot_dispatcher_fx._max_queue_sizes.items())

    processes_names = ('p1', 'p2')
    assert robot_dispatcher_fx.processes
    assert all(i in processes_names for i in robot_dispatcher_fx.processes)
    assert len(robot_dispatcher_fx.processes) == len(processes_names)

    m = ("messages1", "messages2")
    assert all(i in m for i in robot_dispatcher_fx.processes["p1"]["publish_queues"])
    assert len(m) == len(robot_dispatcher_fx.processes["p1"]["publish_queues"])

    m = ("messages3", "messages4")
    assert all(i in m for i in robot_dispatcher_fx.processes["p1"]["consume_queues"])
    assert len(m) == len(robot_dispatcher_fx.processes["p1"]["consume_queues"])

    assert robot_dispatcher_fx.processes["p1"]["extra_param"] == 5

    assert robot_dispatcher_fx.shared_objects
    assert "test_dict" in robot_dispatcher_fx.shared_objects
    assert "test_bool" in robot_dispatcher_fx.shared_objects

    assert robot_dispatcher_fx.system_queues
    assert all(i in processes_names for i in robot_dispatcher_fx.system_queues)
    assert len(robot_dispatcher_fx.system_queues) == len(processes_names)


def test_correct_watcher(mocker: MockerFixture):
    config = {"processes": {"p1": {}, "p2": {}}}
    processes = {
        "p1": {"process_class": WatcherP1, "keep_alive": False},
        "p2": {"process_class": WatcherP2, "keep_alive": False},
    }
    robot_dispatcher = RobotDispatcher(config, processes, in_cluster=False)

    messages = []
    mocker.patch.object(robot_dispatcher.watcher, "_send_to_ws", lambda m: messages.append(m))

    assert robot_dispatcher.watcher_queue
    assert robot_dispatcher.watcher_queue._maxsize == RobotDispatcher.DEFAULT_QUEUE_SIZE

    robot_dispatcher.start_processes()
    time.sleep(5)

    assert len(messages) == 2
    result = {'names': set(), 'classes': set(), 'data': set()}
    for i in messages:
        result['names'].add(i.process_name)
        result['classes'].add(i.process_class)
        result['data'].add(i.data)

    assert result['names'] == {'p1', 'p2'}
    assert result['classes'] == {'WatcherP1', 'WatcherP2'}
    assert result['data'] == {WatcherP1.TEST_MESSAGE, WatcherP2.TEST_MESSAGE}

    robot_dispatcher.stop_logging()


@pytest.mark.parametrize(
    "robot_dispatcher_class_fx",
    (("config_queue_in_process_twice.yaml",),),
    indirect=True,
)
def test_queue_is_not_in_consume_and_publish(robot_dispatcher_class_fx: tuple):
    class_, config = robot_dispatcher_class_fx
    processes = {"p1": {"process_class": StubProcess}, "p2": {"process_class": StubProcess}, }

    with pytest.raises(Exception) as exc_info:
        class_(config, processes)

    assert f"Process 'p2' has the same queue for consume and publish." in str(exc_info.value)
