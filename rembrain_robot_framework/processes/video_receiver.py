import json
import logging
import os
import time
from typing import Generator, Union

from rembrain_robot_framework import RobotProcess
from rembrain_robot_framework.pack import Unpacker
from rembrain_robot_framework.ws import WsCommandType, WsDispatcher, WsRequest


class VideoReceiver(RobotProcess):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.unpacker = Unpacker()

    def run(self):
        logging.info(f"{self.__class__.__name__} started, name: {self.name}.")

        # ws_channel: Generator = self.ws_connect.pull(
        #     WsRequest(
        #         command=WsCommandType.PULL,
        #         exchange="camera0",
        #         robot_name=os.environ["ROBOT_NAME"],
        #         username=os.environ["ROBOT_NAME"],
        #         password=os.environ["ROBOT_PASSWORD"],
        #     )
        # )

        logging.info("active, start consuming")
        while True:
            response_data: Union[str, bytes] = self.consume()
            try:
                if len(response_data) != 0:
                    if isinstance(response_data, bytes):
                        rgb, depth16, camera = self.unpacker.unpack(response_data)
                        self.shared.camera["camera"] = json.loads(camera)
                        self.publish((rgb, depth16, camera), queue_name="video_to_ml", clear_on_overflow=True)
                    else:
                        logging.error(f"VideoReceiver(processor): WS response is not bytes! Response={response_data}.")
            except Exception as e:
                logging.error(f"Error in video_receiver {e}.")

            time.sleep(0.01)
