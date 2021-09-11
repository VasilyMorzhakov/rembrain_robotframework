import os
import typing as T
from multiprocessing import Queue

from rembrain_robotframework import RobotProcess
from rembrain_robotframework.src.ws import WsDispatcher, WsRequest


class WsBaseProcess(RobotProcess):
    def __init__(
            self,
            exchange: str,
            queue: Queue,
            robot_name: T.Optional[str] = None,
            username: T.Optional[str] = None,
            password: T.Optional[str] = None,
            *args,
            **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.ws_connect = WsDispatcher()
        self.exchange: str = exchange
        self.queue: Queue = queue

        self.robot_name: str = robot_name if robot_name else os.environ["ROBOT_NAME"]
        self.username: str = username if username else os.environ["ROBOT_NAME"]
        self.password: str = password if password else os.environ["ROBOT_PASSWORD"]

    def ws_type(self) -> str:
        raise NotImplementedError()

    def ws_request(self):
        return WsRequest(
            command=self.ws_type(),
            exchange=self.exchange,
            robot_name=self.robot_name,
            username=self.username,
            password=self.password,
        )
