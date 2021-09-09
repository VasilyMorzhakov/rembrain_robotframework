import json
import logging
import os
import time
import typing as T
from json.decoder import JSONDecodeError

from rembrain_robotframework import RobotProcess
from rembrain_robotframework.src.ws.command_type import WsCommandType
from rembrain_robotframework.src.ws.dispatcher import WsDispatcher
from rembrain_robotframework.src.ws.request import WsRequest


class CommandReceiver(RobotProcess):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ws_connect = WsDispatcher()

    def run(self) -> None:
        logging.info(f"{self.__class__.__name__} started, name: {self.name}.")

        ws_channel: T.Generator = self.ws_connect.pull(WsRequest(
            command=WsCommandType.PULL,
            exchange="commands",
            robot_name=os.environ["ROBOT_NAME"],
            username=os.environ["ROBOT_NAME"],
            password=os.environ["ROBOT_PASSWORD"],
        ))

        while True:
            response_data: T.Union[str, bytes] = next(ws_channel)

            try:
                if isinstance(response_data, bytes):
                    decoded_command: str = response_data.decode("utf-8")
                    logging.info(f"Received command: {decoded_command}")
                    self.publish(json.loads(decoded_command), queue_name="websocket_to_robot")
                else:
                    logging.error(
                        f"{self.__class__.__name__}: WS response is not bytes! "
                        f"Received: {response_data}, type={type(response_data)}."
                    )
                    break

            except (UnicodeDecodeError, JSONDecodeError):
                logging.warning("UnicodeDecodeError or JSONDecoderError was received.")

        time.sleep(2.0)
        try:
            if isinstance(response_data, bytes):
                decoded_command: str = response_data.decode("utf-8")
                logging.info(f"Received command: {decoded_command}")
                self.publish(json.loads(decoded_command))
            else:
                logging.error(
                    f"{self.__class__.__name__}: WS response is not bytes! "
                    f"Received: {response_data}, type={type(response_data)}."
                )

        except (UnicodeDecodeError, JSONDecodeError):
            logging.warning("UnicodeDecodeError or JSONDecoderError was received.")
