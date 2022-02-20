import asyncio
import json
import typing as T

import websockets
from pika.exchange_type import ExchangeType

from rembrain_robot_framework import RobotProcess
from rembrain_robot_framework.enums.ws_type import WsType
from rembrain_robot_framework.models.request import Request
from rembrain_robot_framework.models.ws_bind_request import WsBindRequest
from rembrain_robot_framework.utils import get_arg_with_env_fallback
from rembrain_robot_framework.ws import WsCommandType, WsRequest
from rembrain_robot_framework.ws.ws_log_adapter import WsLogAdapter


class WsRobotProcess(RobotProcess):
    """
    Process that communicates with a remote websocket server.
    Pulling/pushing data between the program and the weboscket exchange.

    This is the process you should be using if you want to set up distributed processing of your robot's functionality.
    For example, you can have your robot push the video feed to the websocket server, and then have an ML-capable PC
    pull the video feed and perform the ML processing, sending back commands for robot to execute.

    Args:
        **[Required]** command_type: Either `pull` or `push`. Pull to get data from the remote exchange.
        Push to push data to the exchange.

        **[Required]** exchange: Name of the exchange the data should be pushed/pulled from.

        url: Websocket gate URL. If not specified, `WEBSOCKET_GATE_URL` env var is used.

        robot_name: Robot, for which we are pushing/pulling data. If not specified, `ROBOT_NAME` env var is used.

        username: Username of user to log in into the exchange. If not specified, `RRF_USERNAME` env var is used.

        password: Password of user to log in into the exchange. If not specified, `RRF_PASSWORD` env var is used.

        is_service: Flag for using by services - they work with personal messages. Default value: False.

        data_type: (For pull commands) Determines how the binary data from the exchange should be processed.
        The output from the WsRobotProcess to the queues will be of the according data_type.
        Possible values (default: binary): `["json", "binary", "bytes", "str", "string"]`.

        ping_interval: Interval between pings that are being sent to the exchange in seconds. Default value: 1.0

        connection_timeout: Timeout for opening connection to the exchange in seconds. Default value: 1.5
    """

    # Functions to handle binary data coming from pull commands
    _DATA_TYPE_PARSERS: T.Dict[str, T.Callable[[bytes], T.Any]] = {
        "json": lambda b: json.loads(b.decode("utf-8")),
        "str": lambda b: b.decode("utf-8"),
        "string": lambda b: b.decode("utf-8"),
        "bytes": lambda b: b,
        "binary": lambda b: b,
        "request": lambda b: Request.from_bson(b),
        "bind_request": lambda b: WsBindRequest.from_bson(b),
    }

    def __init__(self, *args, **kwargs):
        super(WsRobotProcess, self).__init__(*args, **kwargs)

        self.command_type: str = kwargs["command_type"]
        if self.command_type not in (
            WsCommandType.PUSH,
            WsCommandType.PULL,
            WsCommandType.PUSH_LOOP,
        ):
            raise RuntimeError("Unknown/disallowed command type.")

        # todo actually this process works only with push_loop and pull! It requires refactoring!
        if self.command_type == WsCommandType.PUSH:
            self.command_type = WsCommandType.PUSH_LOOP

        self.exchange: str = kwargs["exchange"]
        self.exchange_type: str = kwargs.get("exchange_type", ExchangeType.fanout.value)
        self.exchange_bind_key: str = kwargs.get("exchange_bind_key", "")

        self.ws_url: str = get_arg_with_env_fallback(
            kwargs, "url", "WEBSOCKET_GATE_URL"
        )
        self.robot_name: str = get_arg_with_env_fallback(
            kwargs, "robot_name", "ROBOT_NAME"
        )
        self.username: str = get_arg_with_env_fallback(
            kwargs, "username", "RRF_USERNAME"
        )
        self.password: str = get_arg_with_env_fallback(
            kwargs, "password", "RRF_PASSWORD"
        )

        self.ws_type: str = kwargs.get("ws_type", WsType.DEFAULT)

        # Data type handling for pull commands
        self.data_type: str = kwargs.get("data_type", "binary").lower()
        if self.data_type not in self._DATA_TYPE_PARSERS:
            raise RuntimeError(
                f"Data type {self.data_type} is not in allowed types.\r\n"
                f"Please use one of following: {', '.join(self._DATA_TYPE_PARSERS.keys())}"
            )

        self._parser = self._DATA_TYPE_PARSERS[self.data_type]
        self.ping_interval = float(kwargs.get("ping_interval", 1.0))
        self.connection_timeout = float(kwargs.get("connection_timeout", 1.5))

    def run(self) -> None:
        self.log.info(f"{self.__class__.__name__} started, name: {self.name}")

        if self.command_type == WsCommandType.PULL:
            asyncio.run(self._connect_ws(self._pull_callback))
        elif self.command_type == WsCommandType.PUSH_LOOP:
            asyncio.run(self._connect_ws(self._push_loop_callback))

    async def _pull_callback(self, ws):
        while True:
            data = await ws.recv()

            # Handles incoming data from websocket
            # If it's in binary, then it's a data packet
            # that should be handled according to the process's data_type
            # If it's a string, then it's a control(ping) packet
            if type(data) is bytes:
                parsed = self._parser(data)

                if self.ws_type == WsType.CLIENT:
                    # parsed is Request
                    self.respond_to(
                        personal_message_uid=parsed.uid,
                        client_process=parsed.client_process,
                        data=parsed.data,
                    )
                elif self.ws_type == WsType.SERVER:
                    # parsed is WsBindRequest
                    self.publish(parsed)
                else:
                    self.publish(parsed)

            # Strings are received only for control packets - right now it's only pings
            elif type(data) is str and data != WsCommandType.PING:
                raise RuntimeError(
                    f"Got non-ping string data from websocket, this shouldn't be happening.\r\n"
                    f"Data: {data}"
                )

    async def _push_loop_callback(self, ws):
        """
        Push handler has three long running function:
        - one for sending pings in keep_alive interval
        - one for consuming from queue and publishing
        - one for receiving and dropping any packages coming from the websocket
        """
        await asyncio.gather(
            self._ping(ws), self._send_to_ws(ws), self._silent_recv(ws)
        )

    async def _connect_ws(self, callback) -> None:
        """
        Connects to the websocket, sends control packet
        then runs handler_fn that then uses the websocket however it needs
        """

        async with websockets.connect(
            self.ws_url,
            logger=WsLogAdapter(self.log, {}),
            open_timeout=self.connection_timeout,
            max_size=None,
        ) as ws:
            try:
                self.log.info("Sending control packet")

                await ws.send(self._get_control_packet())
                await callback(ws)

                self.log.info("Handler function exited")
            except websockets.ConnectionClosedError as e:
                msg = "Connection closed with error."
                if e.rcvd is not None:
                    msg += f" Reason: {e.rcvd.reason}"

                self.log.error(msg)

            except websockets.ConnectionClosedOK as e:
                msg = "Connection closed."
                if e.rcvd is not None:
                    msg += f" Reason: {e.rcvd.reason}"

                self.log.info(msg)

    async def _ping(self, ws):
        """Sends out ping packet ever self.ping_interval seconds"""
        control_packet = json.dumps({"command": WsCommandType.PING})
        while True:
            await asyncio.sleep(self.ping_interval)
            await ws.send(control_packet)

    async def _send_to_ws(self, ws):
        """Gets data to send from the consume_queue (MUST be binary) and sends it to websocket"""
        while True:
            if self.is_empty():
                await asyncio.sleep(0.01)
                continue

            if self.ws_type == WsType.CLIENT:
                personal_message: Request = self.get_request()
                data: bytes = personal_message.to_bson()
            elif self.ws_type == WsType.SERVER:
                personal_bind_message: WsBindRequest = self.consume()
                data: bytes = personal_bind_message.to_bson()
            else:
                data: bytes = self.consume()

            if not isinstance(data, bytes):
                self.log.error(f"Trying to send non-binary data to push: {data}")
                raise RuntimeError("Data to send to ws should be binary")

            await ws.send(data)

    async def _silent_recv(self, ws):
        """Receive and drop incoming packets"""
        while True:
            await ws.recv()

    def _get_control_packet(self) -> str:
        extra_params = {}
        if self.exchange_type == ExchangeType.topic.value:
            extra_params["exchange_type"] = self.exchange_type
            extra_params["exchange_bind_key"] = self.exchange_bind_key

        return WsRequest(
            command=self.command_type,
            exchange=self.exchange,
            robot_name=self.robot_name,
            username=self.username,
            password=self.password,
            **extra_params,
        ).json()
