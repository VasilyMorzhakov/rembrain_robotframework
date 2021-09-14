import json
import logging
import os
from typing import Generator, Union

from rembrain_robot_framework import RobotProcess
from rembrain_robot_framework.ws import WsCommandType, WsDispatcher, WsRequest


class AmqpReceiver(RobotProcess):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.shared.update_config.value = False
        self.ws_connect = WsDispatcher()

    def run(self):
        logging.info(f"Started AmqpReceiver process, name: {self.name}.")
        ws_channel: Generator = self.ws_connect.pull(WsRequest(
            command=WsCommandType.PULL,
            exchange="processor_commands",
            robot_name=os.environ["ROBOT_NAME"],
            username=os.environ["ROBOT_NAME"],
            password=os.environ["ROBOT_PASSWORD"],
        ))

        while True:
            response_data: Union[str, bytes] = next(ws_channel)
            logging.info(f"Command received {response_data}, of type {type(response_data)}")

            if not isinstance(response_data, bytes):
                logging.error("AmqpReceiver: WS response is not bytes! Please, check it.")
                continue

            command = json.loads(response_data.decode(encoding="utf-8"))
            if command["message"] == "update_config":
                self.shared.update_config.value = True
            else:
                logging.warning(f"Unprocessed command recieved: {command}")
