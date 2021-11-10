from unittest.mock import DEFAULT

import pytest
import websocket
from _pytest.fixtures import SubRequest
from pytest_mock import MockerFixture

from rembrain_robot_framework.ws import WsDispatcher, WsRequest, WsCommandType


@pytest.fixture()
def ws_test_data() -> str:
    return "TEST MESSAGE!"


@pytest.fixture()
def ws_request_fx(request: SubRequest) -> WsRequest:
    return WsRequest(command=request.param, exchange='test_ws_dispatcher', robot_name='tester')


@pytest.fixture()
def ws_dispatcher_fx(mocker: MockerFixture, ws_test_data: str) -> WsDispatcher:
    wsd = WsDispatcher()
    wsd.ws = websocket.WebSocket()

    mocker.patch.multiple(wsd, open=DEFAULT, close=DEFAULT)
    mocker.patch.multiple(wsd.ws, send=DEFAULT, recv=lambda: ws_test_data)
    wsd.ws.connected = True

    return wsd


@pytest.mark.parametrize('ws_request_fx', (WsCommandType.PULL,), indirect=True)
def test_correct_ws_pull(ws_dispatcher_fx: WsDispatcher, ws_request_fx: WsRequest, ws_test_data: str) -> None:
    wsd_pull = ws_dispatcher_fx.pull(ws_request_fx)
    assert ws_test_data == next(wsd_pull)


@pytest.mark.parametrize('ws_request_fx', (WsCommandType.PUSH,), indirect=True)
def test_correct_ws_push(ws_dispatcher_fx: WsDispatcher, ws_request_fx: WsRequest, ws_test_data: str) -> None:
    assert ws_test_data == ws_dispatcher_fx.push(ws_request_fx)


@pytest.mark.parametrize('ws_request_fx', (WsCommandType.PUSH_LOOP,), indirect=True)
def test_correct_ws_push_loop(mocker, ws_dispatcher_fx: WsDispatcher, ws_request_fx: WsRequest,
                              ws_test_data: str) -> None:
    test_response = None

    def ws_send(request):
        nonlocal test_response
        test_response = request

    mocker.patch.object(ws_dispatcher_fx, '_start_silent_reader')

    push_loop = ws_dispatcher_fx.push_loop(ws_request_fx)
    next(push_loop)

    mocker.patch.multiple(ws_dispatcher_fx.ws, send=ws_send)
    push_loop.send(ws_test_data)
    assert ws_test_data == test_response

#
# def _tr(i):
#     ws = WsDispatcher()
#     ws.open()
#     _tr.l[i] = ws.ws.connected
#     while True:
#         ws.ws.ping()
#         sleep(2)
#
#
# _tr.l = {}
#
#
# def test_process_loading() -> None:
#     from unittest import mock
#
#     connect_counts = 20
#     env_overrides = {"WEBSOCKET_GATE_URL": "wss://monitor-dev.rembrain.ai:5443", }
#
#     with mock.patch.dict("os.environ", env_overrides):
#         for i in range(1, connect_counts + 1):
#             Process(target=_tr, daemon=True, args=(i,)).start()
#
#     sleep(30)
#     assert len(_tr.l) == connect_counts
