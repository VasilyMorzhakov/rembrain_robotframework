from multiprocessing import Queue
import time
from queue import Empty

import pytest
from pytest_mock import MockerFixture

from rembrain_robot_framework import RobotProcess
from rembrain_robot_framework.utils import ConfigurationError


@pytest.fixture()
def default_proc_params_fx() -> dict:
    return {
        "name": "rp",
        "shared_objects": {},
        "consume_queues": {},
        "publish_queues": {},
        "system_queues": {},
        "watcher_queue": None,
    }


def test_correct_clear_queue(default_proc_params_fx: dict) -> None:
    q1 = Queue(maxsize=2)
    q1.put("q1")
    q1.put("q2")
    time.sleep(2)

    default_proc_params_fx.update(consume_queues={"message1": q1})
    r = RobotProcess(**default_proc_params_fx)
    r.queues_to_clear = ["message1"]
    r.clear_queues()

    with pytest.raises(Empty):
        r.consume_queues["message1"].get(timeout=2)


def test_correct_publish_and_consume(default_proc_params_fx: dict) -> None:
    test_message = "TEST_MESSAGE"
    common_queue = Queue(maxsize=2)

    default_proc_params_fx.update(
        consume_queues={"message1": common_queue},
        publish_queues={"message1": [common_queue], "message2": [Queue(maxsize=2)]},
    )
    r = RobotProcess(**default_proc_params_fx)

    result = r.publish(test_message, queue_name="message1")
    assert result is None
    assert r.consume() == test_message


def test_incorrect_publish(mocker: MockerFixture, default_proc_params_fx: dict) -> None:
    default_proc_params_fx.update(consume_queues={"message1": Queue(maxsize=2)})
    r = RobotProcess(**default_proc_params_fx)

    mocker.patch.object(r.log, "error")
    with pytest.raises(ConfigurationError):
        r.publish("message")

    r._publish_queues = {"message1": [Queue(maxsize=2)], "message2": [Queue(maxsize=2)]}
    with pytest.raises(ConfigurationError):
        r.publish("message")


def test_incorrect_consume(default_proc_params_fx: dict) -> None:
    default_proc_params_fx.update(publish_queues={"message1": Queue(maxsize=2)})
    r = RobotProcess(**default_proc_params_fx)

    with pytest.raises(ConfigurationError):
        r.consume("message1")

    r._consume_queues = {"message1": Queue(maxsize=2), "message2": Queue(maxsize=2)}
    with pytest.raises(ConfigurationError):
        r.consume()


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

    with pytest.raises(ConfigurationError) as exc_info:
        r.is_empty()

    assert 'Process "rp" has no queues to read.' in str(exc_info.value)

    r._consume_queues = {"message1": Queue(maxsize=2), "message2": Queue(maxsize=2)}
    with pytest.raises(ConfigurationError) as exc_info:
        r.is_empty()

    assert "Process 'rp' has more than one read queue. Specify a consume queue name." in str(exc_info.value)

    q = Queue(maxsize=2)
    q.put("q")
    r._consume_queues = {"message1": Queue(maxsize=2), "message2": q}
    assert r.is_empty("message1")
    assert not r.is_empty("message2")
