import numpy as np
import pytest

from rembrain_robot_framework.processes import VideoPacker


@pytest.fixture()
def vp_fx():
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

    color_image = np.zeros((720, 1280, 3))
    color_image[y: y + 100, x: x + 100, 2] = 1
    depth_image = np.zeros((360, 640), dtype=np.int64)
    depth_image[y // 2: y // 2 + 50, x // 2: x // 2 + 50] = 2000
    color_image = (color_image * 255).astype(np.uint8)

    return color_image, depth_image, camera


def test_correct_video_packer(mocker, vp_fx):
    vp = VideoPacker(name="video_packer", shared_objects={"camera": vp_fx[2]}, consume_queues={}, publish_queues={},
                     pack_type=1)
    test_mock_result = None
    loop_reset_exception = 'AssertionError for reset loop!'

    def publish(message, *args):
        nonlocal test_mock_result
        test_mock_result = message
        raise AssertionError(loop_reset_exception)

    mocker.patch.object(vp, 'consume', return_value=vp_fx[0:2])
    mocker.patch.object(vp, 'publish', publish)
    with pytest.raises(AssertionError) as exc_info:
        vp.run()

    assert loop_reset_exception in str(exc_info.value)
    assert isinstance(test_mock_result, bytes)
    assert len(test_mock_result) > 100

