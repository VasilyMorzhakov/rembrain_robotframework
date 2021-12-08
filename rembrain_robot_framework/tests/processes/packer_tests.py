import json

import numpy as np
import pytest
from pytest_mock import MockerFixture

from rembrain_robot_framework.pack import PackType
from rembrain_robot_framework.processes import VideoPacker, VideoUnpacker
from rembrain_robot_framework.services.watcher import Watcher
from rembrain_robot_framework.tests.models import Image


@pytest.fixture()
def img_data_fx():
    return Image.get_data()


@pytest.fixture()
def packer_fx(img_data_fx, request):
    return VideoPacker(
        name="video_packer",
        shared_objects={"camera": img_data_fx.camera},
        consume_queues={},
        publish_queues={},
        system_queues={},
        watcher=Watcher(False),
        pack_type=request.param,
    )


@pytest.fixture()
def unpacker_fx(img_data_fx):
    return VideoUnpacker(
        name="video_unpacker",
        shared_objects={"camera": img_data_fx.camera},
        consume_queues={},
        publish_queues={},
        system_queues={},
        watcher=Watcher(False),
    )


@pytest.mark.parametrize("packer_fx", (PackType.JPG_PNG,), indirect=True)
def test_correct_video_packer(
    mocker: MockerFixture, img_data_fx: Image, packer_fx
) -> None:
    mock_result = None
    loop_reset_exception = "AssertionError for reset loop!"

    def publish(message, *args, **kwargs):
        nonlocal mock_result
        mock_result = message
        raise AssertionError(loop_reset_exception)

    mocker.patch.object(
        packer_fx, "consume", return_value=(img_data_fx.rgb, img_data_fx.depth)
    )
    mocker.patch.object(packer_fx, "publish", publish)
    with pytest.raises(AssertionError) as exc_info:
        packer_fx.run()

    assert loop_reset_exception in str(exc_info.value)
    assert isinstance(mock_result, bytes)
    assert len(mock_result) > 100


@pytest.mark.parametrize("packer_fx", (PackType.JPG,), indirect=True)
def test_correct_full_pack_jpg(
    mocker: MockerFixture, img_data_fx: Image, packer_fx, unpacker_fx
) -> None:
    test_packer_result = None

    def publish(message, *args, **kwargs):
        nonlocal test_packer_result
        test_packer_result = message
        raise AssertionError

    mocker.patch.object(
        packer_fx, "consume", return_value=(img_data_fx.rgb, img_data_fx.depth)
    )
    mocker.patch.object(packer_fx, "publish", publish)
    try:
        packer_fx.run()
    except AssertionError:
        pass

    test_unpacker_result = None
    loop_reset_exception = "BaseException for reset loop!"

    def publish(message, *args, **kwargs):
        nonlocal test_unpacker_result
        test_unpacker_result = message
        # it uses so type of exception because 'VideoUnpacker.run()' absorbs 'Exception'!
        raise BaseException(loop_reset_exception)

    mocker.patch.object(unpacker_fx, "consume", return_value=test_packer_result)
    mocker.patch.object(unpacker_fx, "publish", publish)
    with pytest.raises(BaseException) as exc_info:
        unpacker_fx.run()

    assert loop_reset_exception in str(exc_info.value)
    assert isinstance(test_unpacker_result, tuple)
    assert len(test_unpacker_result) == 3
    assert np.sqrt(np.mean(np.square(test_unpacker_result[0] - img_data_fx.rgb))) < 5
    assert test_unpacker_result[1] is None
    assert "time" in json.loads(test_unpacker_result[2])


@pytest.mark.parametrize("packer_fx", (PackType.JPG_PNG,), indirect=True)
def test_correct_full_pack_png(
    mocker: MockerFixture, img_data_fx: Image, packer_fx, unpacker_fx
) -> None:
    test_packer_result = None

    def publish(message, *args, **kwargs):
        nonlocal test_packer_result
        test_packer_result = message
        raise AssertionError

    mocker.patch.object(
        packer_fx, "consume", return_value=(img_data_fx.rgb, img_data_fx.depth)
    )
    mocker.patch.object(packer_fx, "publish", publish)
    try:
        packer_fx.run()
    except AssertionError:
        pass

    test_unpacker_result = None
    loop_reset_exception = "AssertionError for reset loop!"

    def publish(message, *args, **kwargs):
        nonlocal test_unpacker_result
        test_unpacker_result = message
        raise BaseException(loop_reset_exception)

    mocker.patch.object(unpacker_fx, "consume", return_value=test_packer_result)
    mocker.patch.object(unpacker_fx, "publish", publish)
    with pytest.raises(BaseException) as exc_info:
        unpacker_fx.run()

    assert loop_reset_exception in str(exc_info.value)
    assert isinstance(test_unpacker_result, tuple)
    assert len(test_unpacker_result) == 3
    assert np.sqrt(np.mean(np.square(test_unpacker_result[0] - img_data_fx.rgb))) < 5
    assert (test_unpacker_result[1] == img_data_fx.depth).all()
    assert "time" in test_unpacker_result[2]
