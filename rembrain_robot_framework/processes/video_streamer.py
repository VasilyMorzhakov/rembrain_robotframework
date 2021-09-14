import logging
import os
import time
import typing as T
from datetime import datetime, timezone

from rembrain_robot_framework import RobotProcess
from rembrain_robot_framework.pack import Packer
from rembrain_robot_framework.ws import WsCommandType, WsDispatcher, WsRequest


class VideoStreamer(RobotProcess):
    """ Stream frames are from rgbd_frames queue. """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.ws_connect = WsDispatcher()
        self.packets_sent = 0
        self.last_timed: float = time.time()
        self.packer = Packer(kwargs.get("pack_type"))

    def run(self):
        logging.info(f"{self.__class__.__name__} started, name: {self.name}.")

        request = WsRequest(
            command=WsCommandType.PUSH_LOOP,
            exchange="camera0",
            robot_name=os.environ["ROBOT_NAME"],
            username=os.environ["ROBOT_NAME"],
            password=os.environ["ROBOT_PASSWORD"],
        )

        push_loop = self.ws_connect.push_loop(request)
        next(push_loop)

        while True:
            rgb, depth = self.consume()

            camera: T.Any = self.shared.camera.copy()
            camera["time"] = datetime.now(timezone.utc).timestamp()

            buffer: bytes = self.packer.pack(rgb, depth, camera)
            push_loop.send(buffer)

            self.packets_sent += 1
            if self.packets_sent % 300 == 0:
                logging.info(f"Current video sending rate is {300 / (time.time() - self.last_timed)} fps.")
                self.last_timed = time.time()
