import json
import logging
import os
import typing as T
from rembrain_robotframework import RobotProcess
from rembrain_robotframework.src.ws.command_type import WsCommandType
from rembrain_robotframework.src.ws.dispatcher import WsDispatcher
from rembrain_robotframework.src.ws.request import WsRequest


class WsPullProcess(RobotProcess):
    def __init__(
            self,
            exchange: str,
            queue: str,
            robot_name: T.Optinal[str] = None,
            username: T.Optinal[str] = None,
            password: T.Optinal[str] = None,
            *args,
            is_decode: bool = False,
            **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.ws_connect = WsDispatcher()
        self.exchange: str = exchange
        self.queue: str = queue
        self.is_decode: bool = is_decode

        self.robot_name: str = robot_name if robot_name else os.environ["ROBOT_NAME"]
        self.username: str = username if username else os.environ["ROBOT_NAME"]
        self.password: str = password if password else os.environ["ROBOT_PASSWORD"]

    def run(self):
        logging.info(f"{self.__class__.__name__} started, name: {self.name}.")
        ws_channel: Generator = self.ws_connect.pull(WsRequest(
            command=WsCommandType.PULL,
            exchange=self.exchange,
            robot_name=self.robot_name,
            username=self.username,
            password=self.password,
        ))

        while True:
            response_data: Union[str, bytes] = next(ws_channel)
            if self.is_decode:
                response_data = response_data.decode(encoding="utf-8")

            self.queue.put(response_data)
