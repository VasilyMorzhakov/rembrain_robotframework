import json

import pytest

from rembrain_robot_framework.processes import WsRobotProcess
from rembrain_robot_framework.ws import WsCommandType, WsRequest


# FIXME: don't work after rewrite

@pytest.fixture()
def ws_proc_params_fx():
    return {
        'name': 'ws_robot_process',
        'shared_objects': {},
        'consume_queues': {},
        'publish_queues': {},
        'exchange': 'test_ws_robot_process',
        'robot_name': 'tester',
        'username': 'tester',
        'password': 'tester'
    }


@pytest.mark.skip
def test_correct_ws_push(mocker, ws_proc_params_fx):
    ws_proc = WsRobotProcess(**ws_proc_params_fx, command_type=WsCommandType.PUSH)
    test_mock_result = None
    test_data = {'some_data': 777}
    loop_reset_exception = 'AssertionError for reset loop!'

    def push(request, *args, **kwargs):
        nonlocal test_mock_result
        test_mock_result = request
        raise AssertionError(loop_reset_exception)

    mocker.patch.object(ws_proc, '_ping')
    mocker.patch.object(ws_proc, 'consume', return_value=test_data)
    mocker.patch.object(ws_proc, 'is_empty', return_value=False)
    mocker.patch.object(ws_proc.ws_connect, 'push', push)

    with pytest.raises(AssertionError) as exc_info:
        ws_proc.run()

    assert loop_reset_exception in str(exc_info.value)
    assert isinstance(test_mock_result, WsRequest)
    assert test_mock_result.message == test_data
    assert test_mock_result.exchange == ws_proc.exchange


@pytest.mark.skip
def test_correct_ws_push_loop(mocker, ws_proc_params_fx):
    ws_proc = WsRobotProcess(**ws_proc_params_fx, command_type=WsCommandType.PUSH_LOOP)
    test_mock_result = None
    test_data = {'some_data': 777}
    loop_reset_exception = 'AssertionError for reset loop!'

    def push_loop(*args, **kwargs):
        nonlocal test_mock_result
        test_mock_result = yield
        raise AssertionError(loop_reset_exception)

    mocker.patch.object(ws_proc, '_ping')
    mocker.patch.object(ws_proc, 'consume', return_value=test_data)
    mocker.patch.object(ws_proc, 'is_empty', return_value=False)
    mocker.patch.object(ws_proc.ws_connect, 'push_loop', push_loop)

    with pytest.raises(AssertionError) as exc_info:
        ws_proc.run()

    assert loop_reset_exception in str(exc_info.value)
    assert isinstance(test_mock_result, dict)
    assert test_mock_result == test_data


@pytest.mark.skip
def test_correct_ws_pull(mocker, ws_proc_params_fx):
    ws_proc = WsRobotProcess(**ws_proc_params_fx, command_type=WsCommandType.PULL, is_decode=True, to_json=True)
    test_mock_result = None
    test_data = {'some_data': 777}
    loop_reset_exception = 'AssertionError for reset loop!'

    def pull(*args, **kwargs):
        yield json.dumps(test_data).encode()

    def publish(response_data, *args, **kwargs):
        nonlocal test_mock_result
        test_mock_result = response_data
        raise AssertionError(loop_reset_exception)

    mocker.patch.object(ws_proc, 'publish', publish)
    mocker.patch.object(ws_proc.ws_connect, 'pull', pull)

    with pytest.raises(AssertionError) as exc_info:
        ws_proc.run()

    assert loop_reset_exception in str(exc_info.value)
    assert isinstance(test_mock_result, dict)
    assert test_mock_result == test_data


@pytest.mark.skip
def test_incorrect_command_type(ws_proc_params_fx):
    with pytest.raises(Exception) as exc_info:
        WsRobotProcess(**ws_proc_params_fx, command_type=WsCommandType.PING)

    assert "Unknown/disallowed command type." in str(exc_info.value)


@pytest.mark.skip
def test_incorrect_ws_pull_data_decode(mocker, ws_proc_params_fx):
    ws_proc = WsRobotProcess(**ws_proc_params_fx, command_type=WsCommandType.PULL, is_decode=True)

    def pull(*args, **kwargs):
        yield {'some_data': 777}

    mocker.patch.object(ws_proc.ws_connect, 'pull', pull)
    with pytest.raises(Exception) as exc_info:
        ws_proc.run()

    assert "WS response is not bytes!" in str(exc_info.value)
