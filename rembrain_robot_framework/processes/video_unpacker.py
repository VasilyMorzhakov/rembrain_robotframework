import json
import time
from typing import Union

from rembrain_robot_framework import RobotProcess
from rembrain_robot_framework.pack import Unpacker


class VideoUnpacker(RobotProcess):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.unpacker = Unpacker()

    def run(self):
        self.log.info(f"{self.__class__.__name__} started, name: {self.name}.")
        self.log.info("active, start consuming")

        while True:
            response_data: Union[str, bytes] = self.consume()
            try:
                if len(response_data) != 0:
                    if isinstance(response_data, bytes):
                        rgb, depth16, camera = self.unpacker.unpack(response_data)
                        self.shared.camera["camera"] = json.loads(camera)
                        self.publish((rgb, depth16, camera), clear_on_overflow=True)
                    else:
                        self.log.error(f"VideoReceiver(processor): WS response is not bytes! Response={response_data}.")
            except Exception as e:
                self.log.error(f"Error in video_receiver {e}.")

            time.sleep(0.01)
