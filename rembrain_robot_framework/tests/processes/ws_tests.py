import asyncio
from unittest.mock import MagicMock, AsyncMock

import pytest

from rembrain_robot_framework.processes import WsRobotProcess
from rembrain_robot_framework.tests.exceptions import FinishTestException
from rembrain_robot_framework.ws import WsCommandType


@pytest.fixture()
def ws_proc_params_fx():
    return {
        "name": "ws_robot_process",
        "shared_objects": {},
        "consume_queues": {},
        "publish_queues": {},
        "system_queues": {},
        "command_type": WsCommandType.PULL,
        "exchange": "test_ws_robot_process",
        "url": "https://example.com",
        "robot_name": "tester",
        "username": "tester",
        "password": "tester",
        "watcher_queue": None,
    }


@pytest.fixture()
def ws_proc_push_fx(ws_proc_params_fx, mocker):
    ws_proc_params_fx["command_type"] = WsCommandType.PUSH
    return ws_proc(ws_proc_params_fx, mocker)


@pytest.fixture()
def ws_proc_pull_fx(ws_proc_params_fx, mocker):
    ws_proc_params_fx["command_type"] = WsCommandType.PULL
    return ws_proc(ws_proc_params_fx, mocker)


def ws_proc(ws_proc_params_fx, mocker):
    proc = WsRobotProcess(**ws_proc_params_fx)
    ws_mock = AsyncMock()

    # Context manager that will return the mock
    ws_mock_ctx = mocker.patch("websockets.connect")
    ws_mock_ctx.return_value.__aenter__.return_value = ws_mock

    # WEBSOCKET MOCK SETUP
    # Need to stub out recv and send with some sleep otherwise it hangs the event loop
    async def recv_called(*args):
        await asyncio.sleep(0.05)
        return b"recv_data"

    ws_mock.recv.side_effect = recv_called

    async def send_called(*args):
        await asyncio.sleep(0.05)

    ws_mock.send.side_effect = send_called

    # PROCESS MOCK SETUP
    # Stubbing out is_empty and consume so we always have something to send
    mocker.patch.object(proc, "is_empty", return_value=False)
    mocker.patch.object(proc, "consume", return_value=b"some_data")

    return proc, ws_mock


@pytest.mark.parametrize("arg", ("exchange", "command_type"))
def test_required_args(ws_proc_params_fx, arg):
    del ws_proc_params_fx[arg]
    with pytest.raises(Exception):
        WsRobotProcess(**ws_proc_params_fx)


def test_push_non_binary_fails(mocker, ws_proc_push_fx):
    proc: WsRobotProcess = ws_proc_push_fx[0]
    mocker.patch.object(proc, "consume", return_value="non-binary data")

    with pytest.raises(RuntimeError) as ex:
        proc.run()

    assert "Data to send to ws should be binary" in str(ex.value)


def test_first_thing_sent_is_control_packet(ws_proc_push_fx):
    proc: WsRobotProcess = ws_proc_push_fx[0]
    ws_mock: AsyncMock = ws_proc_push_fx[1]

    async def send_mock(*args):
        raise FinishTestException

    ws_mock.send.side_effect = send_mock

    with pytest.raises(FinishTestException):
        proc.run()

    ws_mock.send.assert_awaited_with(proc.get_control_packet().json())


@pytest.mark.timeout(2)
def test_push_sends_consumed_data(ws_proc_push_fx):
    proc: WsRobotProcess = ws_proc_push_fx[0]
    ws_mock: AsyncMock = ws_proc_push_fx[1]

    packets_consumed = 0

    async def send_mock(*args):
        nonlocal packets_consumed

        if packets_consumed >= 5:
            raise FinishTestException

        packets_consumed += 1
        await asyncio.sleep(0.1)

    ws_mock.send.side_effect = send_mock
    with pytest.raises(FinishTestException):
        proc.run()

    ws_mock.send.assert_awaited_with(proc.consume.return_value)


@pytest.mark.timeout(4)
def test_push_sends_pings(ws_proc_push_fx):
    proc: WsRobotProcess = ws_proc_push_fx[0]
    ws_mock: AsyncMock = ws_proc_push_fx[1]

    async def send_mock(*args):
        packet = args[0]
        if type(packet) is str and "ping" in packet:
            raise FinishTestException

        await asyncio.sleep(0.1)

    ws_mock.send.side_effect = send_mock
    with pytest.raises(FinishTestException):
        proc.run()

    ws_mock.send.assert_awaited_with('{"command": "ping"}')


@pytest.mark.timeout(2)
def test_pull_publishes_received_data(mocker, ws_proc_pull_fx):
    proc: WsRobotProcess = ws_proc_pull_fx[0]

    def publish_mock(*args):
        raise FinishTestException

    pub_mock = MagicMock()
    pub_mock.side_effect = publish_mock
    mocker.patch.object(proc, "publish", pub_mock)

    with pytest.raises(FinishTestException):
        proc.run()

    pub_mock.assert_called_with(b"recv_data")


@pytest.mark.parametrize(
    "data_type,recv_val,expected",
    (
            ("json", b'{"command": "hello"}', {"command": "hello"}),
            ("bytes", b'{"command": "hello"}', b'{"command": "hello"}'),
            ("str", b'{"command": "hello"}', '{"command": "hello"}'),
    ),
)
def test_pull_type_conversion(mocker, ws_proc_params_fx, data_type, recv_val, expected):
    ws_proc_params_fx["data_type"] = data_type
    ws_proc_params_fx["command_type"] = WsCommandType.PULL

    ws_proc_pull = ws_proc(ws_proc_params_fx, mocker)
    proc: WsRobotProcess = ws_proc_pull[0]
    ws_mock: AsyncMock = ws_proc_pull[1]

    def publish_mock(*args):
        raise FinishTestException

    pub_mock = MagicMock()
    pub_mock.side_effect = publish_mock
    mocker.patch.object(proc, "publish", pub_mock)

    async def recv_called(*args):
        await asyncio.sleep(0.05)
        return recv_val

    ws_mock.recv.side_effect = recv_called
    with pytest.raises(FinishTestException):
        proc.run()

    pub_mock.assert_called_with(expected)


def test_pull_doesnt_publish_pings(mocker, ws_proc_pull_fx):
    proc: WsRobotProcess = ws_proc_pull_fx[0]
    ws_mock: AsyncMock = ws_proc_pull_fx[1]
    pings_sent = 0

    async def recv_called(*args):
        nonlocal pings_sent
        pings_sent += 1

        if pings_sent >= 3:
            raise FinishTestException

        await asyncio.sleep(0.05)
        return "ping"

    ws_mock.recv.side_effect = recv_called
    pub_mock = MagicMock()
    mocker.patch.object(proc, "publish", pub_mock)

    with pytest.raises(FinishTestException):
        proc.run()

    pub_mock.assert_not_called()
