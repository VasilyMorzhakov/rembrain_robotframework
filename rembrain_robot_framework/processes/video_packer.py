import time
import typing as T
from datetime import datetime, timezone

from rembrain_robot_framework import RobotProcess
from rembrain_robot_framework.pack import Packer


class VideoPacker(RobotProcess):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.packets_sent = 0
        self.last_timed: float = time.time()
        self.packer = Packer(kwargs.get("pack_type"))

    def run(self):
        self.log.info(f"{self.__class__.__name__} started, name: {self.name}.")

        while True:
            rgb, depth = self.consume()
            camera: T.Any = self.shared.camera.copy()
            camera["time"] = datetime.now(timezone.utc).timestamp()
            buffer: bytes = self.packer.pack(rgb, depth, camera)
            self.publish(buffer)

            self.packets_sent += 1
            if self.packets_sent % 300 == 0:
                self.log.info(f"Current video sending rate is {300 / (time.time() - self.last_timed)} fps.")
                self.last_timed = time.time()
