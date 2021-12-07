from multiprocessing import Queue
import time

import pytest
from pytest_mock import MockerFixture

from rembrain_robot_framework import RobotProcess
from rembrain_robot_framework.services.watcher import Watcher
from rembrain_robot_framework.utils import ConfigurationError


@pytest.fixture()
def default_proc_params_fx() -> dict:
    return {
        'name': 'rp',
        'shared_objects': {},
        'consume_queues': {},
        'publish_queues': {},
        'system_queues': {},
        'watcher': Watcher(False)
    }


# todo fix it
@pytest.mark.skip
def test_correct_clear_queue(default_proc_params_fx: dict) -> None:
    q1 = Queue(maxsize=2)
    q1.put("q1")
    q1.put("q2")

    default_proc_params_fx.update(consume_queues={"message1": q1})
    r = RobotProcess(**default_proc_params_fx)
    r.queues_to_clear = ["message1"]
    r.clear_queues()
    time.sleep(5)

    # TODO IT DOES NOT CLEAN r.consume_queues['message1'].get() ! Why?!
    # assert r.consume_queues['message1'].get(timeout=2) is None


def test_correct_publish_and_consume(default_proc_params_fx: dict) -> None:
    test_message = "TEST_MESSAGE"
    common_queue = Queue(maxsize=2)

    default_proc_params_fx.update(
        consume_queues={"message1": common_queue},
        publish_queues={"message1": [common_queue], "message2": [Queue(maxsize=2)]}
    )
    r = RobotProcess(**default_proc_params_fx)

    result = r.publish(test_message, queue_name="message1")
    assert result is None
    assert r.consume() == test_message


def test_incorrect_publish(mocker: MockerFixture, default_proc_params_fx: dict) -> None:
    default_proc_params_fx.update(consume_queues={"message1": Queue(maxsize=2)})
    r = RobotProcess(**default_proc_params_fx)

    error_message = ""

    def _error(*args):
        nonlocal error_message
        error_message = args[0]

    mocker.patch.object(r.log, 'error', _error)
    try:
        r.publish("message")
    except ConfigurationError as e:
        pass
    else:
        assert False

    r._publish_queues = {"message1": [Queue(maxsize=2)], "message2": [Queue(maxsize=2)]}
    try:
        r.publish("message")
    except ConfigurationError as e:
        pass
    else:
        assert False


def test_incorrect_consume(mocker: MockerFixture, default_proc_params_fx: dict) -> None:
    default_proc_params_fx.update(publish_queues={"message1": Queue(maxsize=2)})
    r = RobotProcess(**default_proc_params_fx)

    try:
        r.consume("message1")
    except ConfigurationError as e:
        pass
    else:
        assert False

    r._consume_queues = {"message1": Queue(maxsize=2), "message2": Queue(maxsize=2)}
    try:
        r.consume()
    except ConfigurationError as e:
        pass
    else:
        assert False


def test_check_is_full(default_proc_params_fx: dict) -> None:
    q1 = Queue(maxsize=2)
    q1.put("q1")
    q1.put("q2")

    q2 = Queue(maxsize=2)
    q2.put("q1")

    default_proc_params_fx.update(
        consume_queues={"message1": q1, "message2": q2},
        publish_queues={"message1": [q2, q1], "message2": [q2]},
    )
    r = RobotProcess(**default_proc_params_fx)

    assert r.is_full(consume_queue_name="message1")
    assert not r.is_full(consume_queue_name="message2")
    assert r.is_full(publish_queue_name="message1")
    assert not r.is_full(publish_queue_name="message2")


def test_check_is_empty(default_proc_params_fx: dict) -> None:
    r = RobotProcess(**default_proc_params_fx)

    with pytest.raises(Exception) as exc_info:
        r.is_empty()

    assert 'Process "rp" has no queues to read.' in str(exc_info.value)

    r._consume_queues = {"message1": Queue(maxsize=2), "message2": Queue(maxsize=2)}
    with pytest.raises(Exception) as exc_info:
        r.is_empty()

    assert "Process 'rp' has more than one read queue. Specify a consume queue name." in str(exc_info.value)

    q = Queue(maxsize=2)
    q.put("q")
    r._consume_queues = {"message1": Queue(maxsize=2), "message2": q}
    assert r.is_empty("message1")
    assert not r.is_empty("message2")
