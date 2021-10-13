import json

import numpy as np
import pytest
from pydantic import BaseModel
from pytest_mock import MockerFixture

from rembrain_robot_framework.pack import PackType
from rembrain_robot_framework.processes import VideoPacker, VideoUnpacker


class ImgData(BaseModel):
    image: np.ndarray
    depth: np.ndarray
    camera: dict

    class Config:
        arbitrary_types_allowed = True


@pytest.fixture()
def img_data_fx():
    x = 200
    y = 100
    camera = {
        "fx": 1000,
        "fy": 1000,
        "ppx": 640,
        "ppy": 360,
        "width": 1280,
        "height": 720,
    }

    color_image: np.ndarray = np.zeros((720, 1280, 3))
    color_image[y: y + 100, x: x + 100, 2] = 1
    color_image = (color_image * 255).astype(np.uint8)

    depth_image: np.ndarray = np.zeros((360, 640), dtype=np.uint16)
    depth_image[y // 2: y // 2 + 50, x // 2: x // 2 + 50] = 2000

    return ImgData(image=color_image, depth=depth_image, camera=camera)


def test_correct_video_packer(mocker: MockerFixture, img_data_fx: ImgData) -> None:
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

    mocker.patch.object(vp, 'consume', return_value=(img_data_fx.image, img_data_fx.depth))
    mocker.patch.object(vp, 'publish', publish)
    with pytest.raises(AssertionError) as exc_info:
        vp.run()

    assert loop_reset_exception in str(exc_info.value)
    assert isinstance(mock_result, bytes)
    assert len(mock_result) > 100


def test_correct_full_pack_jpg(mocker: MockerFixture, img_data_fx: ImgData) -> None:
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

    mocker.patch.object(vp, 'consume', return_value=(img_data_fx.image, img_data_fx.depth))
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
    assert np.sqrt(np.mean(np.square(test_unpacker_result[0] - img_data_fx.image))) < 5
    assert test_unpacker_result[1] is None
    assert 'time' in json.loads(test_unpacker_result[2])


def test_correct_full_pack_png(mocker: MockerFixture, img_data_fx: ImgData) -> None:
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

    mocker.patch.object(vp, 'consume', return_value=(img_data_fx.image, img_data_fx.depth))
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
    assert np.sqrt(np.mean(np.square(test_unpacker_result[0] - img_data_fx.image))) < 5
    assert (test_unpacker_result[1] == img_data_fx.depth).all()
    assert 'time' in test_unpacker_result[2]
