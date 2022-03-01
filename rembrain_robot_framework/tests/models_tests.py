from rembrain_robot_framework.models.request import Request
from rembrain_robot_framework.models.bind_request import BindRequest


def test_correct_request_bson():
    client_process = "test_client_proc"
    data = b'qwe'

    request_before = Request(client_process=client_process, data=data)
    bs_data: bytes = request_before.to_bson()

    assert isinstance(bs_data, bytes)

    request_after = Request.from_bson(bs_data)
    assert request_after.client_process == client_process
    assert request_after.data == data


def test_correct_ws_bind_request_bson():
    bind_key = "test_bind_key"
    client_process = "test_client_proc"
    data = b'qwe'

    request_before = Request(client_process=client_process, data=data)
    ws_bind_request_before = BindRequest(bind_key=bind_key, request=request_before)
    bs_data: bytes = ws_bind_request_before.to_bson()

    assert isinstance(bs_data, bytes)

    request_after = BindRequest.from_bson(bs_data)
    assert request_after.bind_key == bind_key
    assert request_after.request.client_process == client_process
    assert request_after.request.data == data
