import json
import os
import time
import typing as T

from rembrain_robot_framework import RobotProcess
from rembrain_robot_framework.ws import WsDispatcher, WsRequest, WsCommandType
import hanging_threads

# Per-process singleton so we don't monitor multiple times
monitoring_thread = None

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
        """
        Process for working with websockets.
        It allows send to ws from queue and vice verse.
        :param command_type: value of WsCommandType
        :param exchange: name of exchange for RabbitMQ
        :param robot_name:robot_name
        :param username:robot_name
        :param password:robot_name
        :param args:
        :param kwargs:
        """
        super().__init__(*args, **kwargs)

        # global monitoring_thread
        # if monitoring_thread is not None:
        #     self.log.info("Restarting monitoring thead")
        #     monitoring_thread.stop()
        # monitoring_thread = hanging_threads.start_monitoring(seconds_frozen=5, test_interval=100)

        self.command_type: str = command_type
        if self.command_type not in WsCommandType.ALL_VALUES or self.command_type == WsCommandType.PING:
            raise Exception("Unknown/disallowed command type.")

        self.ws_connect = WsDispatcher(proc_name=self.name)
        self.exchange: str = exchange

        self.robot_name: str = robot_name if robot_name else os.environ["ROBOT_NAME"]
        self.username: str = username if username else os.environ["ROBOT_NAME"]
        self.password: str = password if password else os.environ["ROBOT_PASSWORD"]

        self.is_decode: bool = kwargs.get('is_decode', False)
        self.to_json: bool = kwargs.get('to_json', False)

        # For push/push_loop we're sending a ping in an interval to keep the connection alive
        self.keep_alive_interval: float = float(kwargs.get('keep_alive_interval', 1.0))
        self.last_ping_time: T.Optional[float] = None

        self.retry_push: T.Union[str, int, None] = kwargs.get('retry_push')
        if self.retry_push:
            self.retry_push = int(self.retry_push)

    def get_ws_request(self, command_type: T.Optional[str] = None) -> WsRequest:
        if command_type is None:
            command_type = self.command_type

        return WsRequest(
            command=command_type,
            exchange=self.exchange,
            robot_name=self.robot_name,
            username=self.username,
            password=self.password,
        )

    def run(self) -> None:
        self.log.info(f"{self.__class__.__name__} started, name: {self.name}.")
        self.last_ping_time = time.time()

        if self.command_type == WsCommandType.PULL:
            self._pull()
        elif self.command_type == WsCommandType.PUSH:
            self._push()
        elif self.command_type == WsCommandType.PUSH_LOOP:
            self._push_loop()

    def _pull(self) -> None:
        ws_channel: T.Generator = self.ws_connect.pull(self.get_ws_request())

        while True:
            response_data: T.Union[str, bytes] = next(ws_channel)

            self.log.debug(f"Got data: {response_data}")

            if self.is_decode:
                if not isinstance(response_data, bytes):
                    error_message = f"{self.__class__.__name__}: WS response is not bytes!"
                    self.log.error(error_message)
                    raise Exception(error_message)

                response_data = response_data.decode(encoding="utf-8")

            if self.to_json:
                response_data = json.loads(response_data)

            self.log.debug(f"Publishing data to queue: {response_data}")
            self.publish(response_data)

    def _push(self) -> None:
        request = self.get_ws_request()

        while True:
            if self.is_empty():
                self._ping()
            else:
                request.message = self.consume()
                self.ws_connect.push(request, retry_times=self.retry_push)

    def _push_loop(self) -> None:
        push_loop: T.Generator = self.ws_connect.push_loop(self.get_ws_request())
        next(push_loop)

        while True:
            if self.is_empty():
                self._ping(push_loop)
            else:
                push_loop.send(self.consume())

    def _ping(self, push_loop: T.Optional[T.Generator] = None) -> None:
        now: float = time.time()

        if now - self.last_ping_time >= self.keep_alive_interval:
            if push_loop:
                push_loop.send(json.dumps({"command": WsCommandType.PING}))
            else:
                self.ws_connect.push(self.get_ws_request(WsCommandType.PING))

            self.last_ping_time = now

        # This MUST be low because ping polling goes in the same thread as data sending/receiving
        time.sleep(0.001)
