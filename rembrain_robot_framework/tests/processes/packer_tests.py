import json

import numpy as np
import pytest
from pytest_mock import MockerFixture

from rembrain_robot_framework.pack import PackType
from rembrain_robot_framework.processes import VideoPacker, VideoUnpacker
from rembrain_robot_framework.tests.utils import Image


@pytest.fixture()
def img_data_fx():
    return Image.get_data()


def test_correct_video_packer(mocker: MockerFixture, img_data_fx: Image) -> None:
    vp = VideoPacker(
        name="video_packer",
        shared_objects={"camera": img_data_fx.camera},
        consume_queues={},
        publish_queues={},
        pack_type=PackType.JPG_PNG
    )

    mock_result = None
    loop_reset_exception = 'AssertionError for reset loop!'

    def publish(message, *args, **kwargs):
        nonlocal mock_result
        mock_result = message
        raise AssertionError(loop_reset_exception)

    mocker.patch.object(vp, 'consume', return_value=(img_data_fx.rgb, img_data_fx.depth))
    mocker.patch.object(vp, 'publish', publish)
    with pytest.raises(AssertionError) as exc_info:
        vp.run()

    assert loop_reset_exception in str(exc_info.value)
    assert isinstance(mock_result, bytes)
    assert len(mock_result) > 100


def test_correct_full_pack_jpg(mocker: MockerFixture, img_data_fx: Image) -> None:
    vp = VideoPacker(
        name="video_packer",
        shared_objects={"camera": img_data_fx.camera},
        consume_queues={},
        publish_queues={},
        pack_type=PackType.JPG
    )

    test_packer_result = None

    def publish(message, *args, **kwargs):
        nonlocal test_packer_result
        test_packer_result = message
        raise AssertionError

    mocker.patch.object(vp, 'consume', return_value=(img_data_fx.rgb, img_data_fx.depth))
    mocker.patch.object(vp, 'publish', publish)
    try:
        vp.run()
    except AssertionError:
        pass

    vp = VideoUnpacker(
        name="video_unpacker",
        shared_objects={"camera": img_data_fx.camera},
        consume_queues={},
        publish_queues={},
    )

    test_unpacker_result = None
    loop_reset_exception = 'BaseException for reset loop!'

    def publish(message, *args, **kwargs):
        nonlocal test_unpacker_result
        test_unpacker_result = message
        # it uses so type of exception because 'VideoUnpacker.run()' absorbs 'Exception'!
        raise BaseException(loop_reset_exception)

    mocker.patch.object(vp, 'consume', return_value=test_packer_result)
    mocker.patch.object(vp, 'publish', publish)
    with pytest.raises(BaseException) as exc_info:
        vp.run()

    assert loop_reset_exception in str(exc_info.value)
    assert isinstance(test_unpacker_result, tuple)
    assert len(test_unpacker_result) == 3
    assert np.sqrt(np.mean(np.square(test_unpacker_result[0] - img_data_fx.rgb))) < 5
    assert test_unpacker_result[1] is None
    assert 'time' in json.loads(test_unpacker_result[2])


def test_correct_full_pack_png(mocker: MockerFixture, img_data_fx: Image) -> None:
    vp = VideoPacker(
        name="video_packer",
        shared_objects={"camera": img_data_fx.camera},
        consume_queues={},
        publish_queues={},
        pack_type=PackType.JPG_PNG
    )

    test_packer_result = None

    def publish(message, *args, **kwargs):
        nonlocal test_packer_result
        test_packer_result = message
        raise AssertionError

    mocker.patch.object(vp, 'consume', return_value=(img_data_fx.rgb, img_data_fx.depth))
    mocker.patch.object(vp, 'publish', publish)
    try:
        vp.run()
    except AssertionError:
        pass

    vp = VideoUnpacker(
        name="video_unpacker",
        shared_objects={"camera": img_data_fx.camera},
        consume_queues={},
        publish_queues={},
    )

    test_unpacker_result = None
    loop_reset_exception = 'AssertionError for reset loop!'

    def publish(message, *args, **kwargs):
        nonlocal test_unpacker_result
        test_unpacker_result = message
        raise BaseException(loop_reset_exception)

    mocker.patch.object(vp, 'consume', return_value=test_packer_result)
    mocker.patch.object(vp, 'publish', publish)
    with pytest.raises(BaseException) as exc_info:
        vp.run()

    assert loop_reset_exception in str(exc_info.value)
    assert isinstance(test_unpacker_result, tuple)
    assert len(test_unpacker_result) == 3
    assert np.sqrt(np.mean(np.square(test_unpacker_result[0] - img_data_fx.rgb))) < 5
    assert (test_unpacker_result[1] == img_data_fx.depth).all()
    assert 'time' in test_unpacker_result[2]
