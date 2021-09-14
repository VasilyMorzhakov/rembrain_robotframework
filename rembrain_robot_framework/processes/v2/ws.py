import logging
import os
import typing as T

from rembrain_robot_framework import RobotProcess
from rembrain_robot_framework.ws import WsDispatcher, WsRequest, WsCommandType


class WsRobotProcess(RobotProcess):
    def __init__(
            self,
            command_type: str,
            exchange: str,
            robot_name: T.Optional[str] = None,
            username: T.Optional[str] = None,
            password: T.Optional[str] = None,
            *args,
            **kwargs
    ):
        super().__init__(*args, **kwargs)

        self.command_type: str = command_type
        if self.command_type not in WsCommandType.ALL_VALUES or self.command_type == WsCommandType.PING:
            raise Exception("Unknown/disallowed command type.")

        self.ws_connect = WsDispatcher()
        self.exchange: str = exchange

        self.robot_name: str = robot_name if robot_name else os.environ["ROBOT_NAME"]
        self.username: str = username if username else os.environ["ROBOT_NAME"]
        self.password: str = password if password else os.environ["ROBOT_PASSWORD"]

        self.is_decode: bool = kwargs.get('is_decode', False)

    def get_ws_request(self) -> WsRequest:
        return WsRequest(
            command=self.command_type,
            exchange=self.exchange,
            robot_name=self.robot_name,
            username=self.username,
            password=self.password,
        )

    def run(self) -> None:
        logging.info(f"{self.__class__.__name__} started, name: {self.name}.")

        if self.command_type == WsCommandType.PULL:
            self._pull()
        elif self.command_type == WsCommandType.PUSH:
            self._push()
        elif self.command_type == WsCommandType.PUSH_LOOP:
            self._push_loop()
        else:
            raise Exception("Unknown type of ws command type.")

    # todo what about time?
    def _pull(self) -> None:
        ws_channel: T.Generator = self.ws_connect.pull(self.get_ws_request())

        while True:
            response_data: T.Union[str, bytes] = next(ws_channel)

            if self.is_decode:
                if not isinstance(response_data, bytes):
                    error_message = f"{self.__class__.__name__}: WS response is not bytes!"
                    logging.error(error_message)
                    raise Exception(error_message)

                response_data = response_data.decode(encoding="utf-8")

            self.publish(response_data)

    # todo what about time?
    def _push(self):
        request = self.get_ws_request()

        while True:
            request.message = self.consume()
            self.ws_connect.push(request)

    # todo what about time?
    def _push_loop(self):
        push_loop: T.Generator = self.ws_connect.push_loop(self.get_ws_request())
        next(push_loop)

        while True:
            push_loop.send(self.consume())
