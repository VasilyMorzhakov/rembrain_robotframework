import json
import logging
import os
from typing import Union, Generator

from robot_framework import RobotProcess
from robot_framework.src.ws.command_type import WsCommandType
from robot_framework.src.ws.dispatcher import WsDispatcher
from robot_framework.src.ws.request import WsRequest


class StateReceiver(RobotProcess):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ws_connect = WsDispatcher()

    def run(self):
        logging.info(f"Started state receiver process, name: {self.name}.")
        ws_channel: Generator = self.ws_connect.pull(
            WsRequest(
                command=WsCommandType.PULL,
                exchange="state",
                robot_name=os.environ["ROBOT_NAME"],
                username=os.environ["ROBOT_NAME"],
                password=os.environ["ROBOT_PASSWORD"],
            )
        )

        while True:
            response_data: Union[str, bytes] = next(ws_channel)
            if not isinstance(response_data, bytes):
                logging.error("RabbitStateReceiver: WS response is not bytes! Please, check it.")
                continue

            status = json.loads(response_data.decode("utf-8"))
            if status["state_machine"] == "NEED_ML":
                if not self.shared.ask_for_ml.value:
                    logging.info("ask_for_ml.value=True")

                self.shared.ask_for_ml.value = True
            else:
                self.shared.ask_for_ml.value = False

            for k, v in status.items():
                self.shared.status[k] = v
