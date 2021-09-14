import logging
import os
import typing as T

import numpy as np

from rembrain_robot_framework import RobotProcess
from rembrain_robot_framework.ws import WsCommandType, WsDispatcher, WsRequest


class AudioReceiverSd(RobotProcess):
    """ It receives commands from server and sends them to the robot (supervisor). """

    def __init__(self, exchange_name: str, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.ws_connect = WsDispatcher()
        self.exchange_name = exchange_name

    def run(self):
        logging.info(f"{self.__class__.__name__} started, name: {self.name}.")

        ws_channel: T.Generator = self.ws_connect.pull(
            WsRequest(
                command=WsCommandType.PULL,
                exchange=self.exchange_name,
                robot_name=os.environ["ROBOT_NAME"],
                username=os.environ["ROBOT_NAME"],
                password=os.environ["ROBOT_PASSWORD"],
            )
        )

        while True:
            response_data: T.Union[str, bytes] = next(ws_channel)

            if isinstance(response_data, bytes):
                if self.is_full(publish_queue_name="audio_queue"):
                    logging.warning("Audio queue is overflow.")
                else:
                    self.publish(np.frombuffer(response_data, dtype=np.float32))
            else:
                logging.error(
                    f"{self.__class__.__name__}: WS response is not bytes!"
                    f" Received: {response_data},type={type(response_data)}"
                )
