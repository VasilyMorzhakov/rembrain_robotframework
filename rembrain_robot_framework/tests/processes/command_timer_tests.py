import json

import pytest

from rembrain_robot_framework.processes import CommandTimer
from rembrain_robot_framework.services.watcher import Watcher


@pytest.fixture()
def command_timer_fx():
    return CommandTimer(
        name="command_timer",
        shared_objects={},
        consume_queues={},
        publish_queues={},
        system_queues={},
        watcher_queue=None,
    )


def test_correct_command_timer(mocker, command_timer_fx):
    test_mock_result = {}
    loop_reset_exception = "AssertionError for reset loop!"

    def publish(message: bytes, *args):
        nonlocal test_mock_result
        test_mock_result = json.loads(message.decode())
        raise AssertionError(loop_reset_exception)

    mocker.patch.object(
        command_timer_fx, "consume", return_value=json.dumps({"some_data": 777})
    )
    mocker.patch.object(command_timer_fx, "publish", publish)
    with pytest.raises(AssertionError) as exc_info:
        command_timer_fx.run()

    assert loop_reset_exception in str(exc_info.value)
    assert "timestamp" in test_mock_result
    assert "some_data" in test_mock_result
    assert test_mock_result["some_data"] == 777


def test_incorrect_json_for_command_timer(mocker, command_timer_fx):
    mocker.patch.object(command_timer_fx, "consume", return_value={"some_data": 777})
    with pytest.raises(TypeError) as exc_info:
        command_timer_fx.run()

    assert "JSON object must be str, bytes or bytearray, not dict" in str(
        exc_info.value
    )
