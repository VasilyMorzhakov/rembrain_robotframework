import struct
import typing as T

import cv2
import numpy

from rembrain_robotframework.src.pack import PackType


class Unpacker:
    def __init__(self):
        self.pack_type: int = -1

    def pre_unpack(self, buffer: T.Any) -> tuple:
        if self.pack_type == -1:
            self.pack_type = buffer[0]

        if self.pack_type != buffer[0]:
            raise Exception("Packer type was changed on fly.")

        if self.pack_type == PackType.JPG:
            l1: tuple = struct.unpack("I", buffer[0 + 1: 4 + 1])[0]
            l2: tuple = struct.unpack("I", buffer[4 + 1: 8 + 1])[0]

            if len(buffer) == l1 + l2 + 8 + 1:
                buf1 = buffer[8 + 1: 8 + 1 + l1]
                buf2 = buffer[8 + 1 + l1: 8 + 1 + l1 + l2]
                return buf1, None, buf2.decode("utf-8")

        if self.pack_type == PackType.JPG_PNG:
            l1 = struct.unpack("I", buffer[0 + 1: 4 + 1])[0]
            l2 = struct.unpack("I", buffer[4 + 1: 8 + 1])[0]
            l3 = struct.unpack("I", buffer[8 + 1: 12 + 1])[0]

            if len(buffer) == l1 + l2 + l3 + 12 + 1:
                buf1 = buffer[12 + 1: 12 + 1 + l1]
                buf2 = buffer[12 + 1 + l1: 12 + 1 + l1 + l2]
                buf3 = buffer[12 + 1 + l1 + l2: 12 + 1 + l1 + l2 + l3]

                buf1 = numpy.frombuffer(buf1, dtype=numpy.uint8)
                buf2 = numpy.frombuffer(buf2, dtype=numpy.uint8)

                return buf1, buf2, buf3.decode("utf-8")

        return None, None, None

    def unpack(self, buffer: T.Any) -> tuple:
        if self.pack_type == -1:
            self.pack_type = buffer[0]

        if self.pack_type != buffer[0]:
            raise Exception("packer type was changed on fly.")

        if self.pack_type == PackType.JPG:
            l1 = struct.unpack("I", buffer[0 + 1: 4 + 1])[0]
            l2 = struct.unpack("I", buffer[4 + 1: 8 + 1])[0]

            if len(buffer) == l1 + l2 + 8 + 1:
                buf1 = buffer[8 + 1: 8 + 1 + l1]
                buf2 = buffer[8 + 1 + l1: 8 + 1 + l1 + l2]
                buf1 = numpy.frombuffer(buf1, dtype=numpy.uint8)

                rgb = cv2.imdecode(buf1, cv2.IMREAD_COLOR)
                return rgb, None, buf2.decode("utf-8")

        if self.pack_type == PackType.JPG_PNG:
            l1 = struct.unpack("I", buffer[0 + 1: 4 + 1])[0]
            l2 = struct.unpack("I", buffer[4 + 1: 8 + 1])[0]
            l3 = struct.unpack("I", buffer[8 + 1: 12 + 1])[0]

            if len(buffer) == l1 + l2 + l3 + 12 + 1:
                buf1 = buffer[12 + 1: 12 + 1 + l1]
                buf2 = buffer[12 + 1 + l1: 12 + 1 + l1 + l2]
                buf3 = buffer[12 + 1 + l1 + l2: 12 + 1 + l1 + l2 + l3]

                buf1 = numpy.frombuffer(buf1, dtype=numpy.uint8)
                rgb = cv2.imdecode(buf1, cv2.IMREAD_COLOR)

                buf2 = numpy.frombuffer(buf2, dtype=numpy.uint8)
                depth16 = cv2.imdecode(buf2, flags=-1)

                return rgb, depth16, buf3.decode("utf-8")

        return None, None, None
