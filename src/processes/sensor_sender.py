import logging
import os
from typing import Any

from robot_framework import RobotProcess
from robot_framework.src.ws.command_type import WsCommandType
from robot_framework.src.ws.dispatcher import WsDispatcher
from robot_framework.src.ws.request import WsRequest


class SensorSender(RobotProcess):
    """ It sends messages (like current robot position) to the server."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.ws_connect = WsDispatcher()
        if "to_play" in self.publish_queues:
            self.publish("online", queue_name="to_play")

    def run(self) -> None:
        logging.info(f"{self.__class__.__name__} started, name: {self.name}.")

        request = WsRequest(
            command=WsCommandType.PUSH,
            exchange="state",
            robot_name=os.environ["ROBOT_NAME"],
            username=os.environ["ROBOT_NAME"],
            password=os.environ["ROBOT_PASSWORD"],
        )

        while True:
            message: Any = self.consume()
            request.message=message
            self.ws_connect.push(request)
