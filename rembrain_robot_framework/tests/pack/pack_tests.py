import numpy as np
import pytest
from _pytest.fixtures import SubRequest

from rembrain_robot_framework.pack import PackType, Packer, Unpacker
from rembrain_robot_framework.tests.models import Image


@pytest.fixture()
def img_data_fx():
    return Image.get_data()


@pytest.fixture()
def pack_buffer_fx(request: SubRequest, img_data_fx) -> bytes:
    return Packer(request.param).pack(img_data_fx.rgb, img_data_fx.depth, img_data_fx.camera)


@pytest.mark.parametrize('pack_buffer_fx', (PackType.JPG_PNG, PackType.JPG), indirect=True)
def test_correct_pack(pack_buffer_fx: bytes):
    assert isinstance(pack_buffer_fx, bytes)
    assert len(pack_buffer_fx) > 100


@pytest.mark.parametrize('pack_buffer_fx', (PackType.JPG_PNG,), indirect=True)
def test_correct_full_pack_png(pack_buffer_fx: bytes, img_data_fx: Image) -> None:
    test_unpacker_result = Unpacker().unpack(pack_buffer_fx)

    assert isinstance(test_unpacker_result, tuple)
    assert len(test_unpacker_result) == 3
    assert np.sqrt(np.mean(np.square(test_unpacker_result[0] - img_data_fx.rgb))) < 5
    assert (test_unpacker_result[1] == img_data_fx.depth).all()


@pytest.mark.parametrize('pack_buffer_fx', (PackType.JPG,), indirect=True)
def test_correct_full_pack_jpg(pack_buffer_fx: bytes, img_data_fx: Image) -> None:
    test_unpacker_result = Unpacker().unpack(pack_buffer_fx)

    assert isinstance(test_unpacker_result, tuple)
    assert len(test_unpacker_result) == 3
    assert np.sqrt(np.mean(np.square(test_unpacker_result[0] - img_data_fx.rgb))) < 5
    assert test_unpacker_result[1] is None
