import json
import struct
import typing as T

import cv2
import numpy

from robot_framework.src.pack import PackType


class Packer:
    def __init__(self, pack_type: T.Union[PackType, str]):
        self.pack_type: PackType = PackType[pack_type] if type(pack_type) is str else pack_type
        self.frame_index = 0
        self.encode_param = [cv2.IMWRITE_JPEG_QUALITY, 75]

    def pack(self, rgb_image: T.Any, depth_16bit: T.Any, meta: T.Optional[dict] = None) -> bytes:
        if meta is None:
            meta = {}

        if self.pack_type == PackType.JPG:
            result, encimg = cv2.imencode(".jpg", rgb_image, self.encode_param)
            buf1 = numpy.frombuffer(encimg, dtype=numpy.uint8)
            text = json.dumps(meta)
            buf2 = numpy.frombuffer(text.encode("utf-8"), dtype=numpy.uint8)

            result = numpy.zeros((buf1.shape[0] + buf2.shape[0] + 8 + 1), dtype=numpy.uint8)

            result[0] = int(self.pack_type)
            result[0 + 1: 4 + 1] = numpy.frombuffer(struct.pack("I", buf1.shape[0]), dtype=numpy.uint8)[:]
            result[4 + 1: 8 + 1] = numpy.frombuffer(struct.pack("I", buf2.shape[0]), dtype=numpy.uint8)[:]

            result[8 + 1: 8 + 1 + buf1.shape[0]] = buf1[:]
            result[8 + 1 + buf1.shape[0]: 8 + 1 + buf1.shape[0] + buf2.shape[0]] = buf2[:]
            return result.tobytes()

        if self.pack_type == PackType.JPG_PNG:
            result, encimg = cv2.imencode(".png", depth_16bit)
            buf2 = numpy.frombuffer(encimg, dtype=numpy.uint8)

            result, encimg = cv2.imencode(".jpg", rgb_image, self.encode_param)
            buf1 = numpy.frombuffer(encimg, dtype=numpy.uint8)

            meta["frameindex"] = self.frame_index
            text = json.dumps(meta)
            self.frame_index += 1

            buf3 = numpy.frombuffer(text.encode("utf-8"), dtype=numpy.uint8)
            result = numpy.zeros((buf1.shape[0] + buf2.shape[0] + buf3.shape[0] + 12 + 1), dtype=numpy.uint8)

            result[0] = int(self.pack_type)
            result[0 + 1: 4 + 1] = numpy.frombuffer(struct.pack("I", buf1.shape[0]), dtype=numpy.uint8)[:]
            result[4 + 1: 8 + 1] = numpy.frombuffer(struct.pack("I", buf2.shape[0]), dtype=numpy.uint8)[:]
            result[8 + 1: 12 + 1] = numpy.frombuffer(struct.pack("I", buf3.shape[0]), dtype=numpy.uint8)[:]

            result[12 + 1: 12 + 1 + buf1.shape[0]] = buf1[:]
            result[12 + 1 + buf1.shape[0]: 12 + 1 + buf1.shape[0] + buf2.shape[0]] = buf2[:]
            result[12 + 1 + buf1.shape[0] + buf2.shape[0]:] = buf3[:]

            return result.tobytes()

        raise Exception(f"Unknown type of packer: {self.pack_type}.")
