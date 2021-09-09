import json
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
            robot_name: T.Optinal[str] = None,
            username: T.Optinal[str] = None,
            password: T.Optinal[str] = None,
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
        push_loop: Generator = self.ws_connect.push_loop(WsRequest(
            command=WsCommandType.PULL,
            exchange=self.exchange,
            robot_name=self.robot_name,
            username=self.username,
            password=self.password,
        ))
        next(push_loop)

        while True:
            push_loop.send(self.queue.get())
