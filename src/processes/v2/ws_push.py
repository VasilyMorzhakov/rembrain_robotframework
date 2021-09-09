import logging
import os
import typing as T

from rembrain_robotframework import RobotProcess
from rembrain_robotframework.src.ws.command_type import WsCommandType
from rembrain_robotframework.src.ws.dispatcher import WsDispatcher
from rembrain_robotframework.src.ws.request import WsRequest


class WsPushLoopProcess(RobotProcess):
    def __init__(
            self,
            exchange: str,
            queue: str,
            robot_name: T.Optional[str] = None,
            username: T.Optional[str] = None,
            password: T.Optional[str] = None,
            *args,
            **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.ws_connect = WsDispatcher()
        self.exchange: str = exchange
        self.queue: str = queue

        self.robot_name: str = robot_name if robot_name else os.environ["ROBOT_NAME"]
        self.username: str = username if username else os.environ["ROBOT_NAME"]
        self.password: str = password if password else os.environ["ROBOT_PASSWORD"]

    def run(self):
        logging.info(f"{self.__class__.__name__} started, name: {self.name}.")
        request = WsRequest(
            command=WsCommandType.PUSH,
            exchange="state",
            robot_name=os.environ["ROBOT_NAME"],
            username=os.environ["ROBOT_NAME"],
            password=os.environ["ROBOT_PASSWORD"],
        )

        while True:
            push_loop.send(self.queue.get())
