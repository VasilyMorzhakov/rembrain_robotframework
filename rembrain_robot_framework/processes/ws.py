import asyncio
import json
import typing as T

import websockets
from pika.exchange_type import ExchangeType

from rembrain_robot_framework import RobotProcess
from rembrain_robot_framework.enums.rpc_user_type import RpcUserType
from rembrain_robot_framework.models.request import Request
from rembrain_robot_framework.models.bind_request import BindRequest
from rembrain_robot_framework.utils import get_arg_with_env_fallback
from rembrain_robot_framework.ws import WsCommandType, WsRequest
from rembrain_robot_framework.ws.log_adapter import WsLogAdapter


# todo divide into 2 classes ?
class WsRobotProcess(RobotProcess):
    """
    Process that communicates with a remote websocket server.
    Pulling/pushing data between the program and the weboscket exchange.

    This is the process you should be using if you want to set up distributed processing of your robot's functionality.
    For example, you can have your robot push the video feed to the websocket server, and then have an ML-capable PC
    pull the video feed and perform the ML processing, sending back commands for robot to execute.

    Args:
        **[Required]** command_type: Either `pull` or `push`.
        Pull to get data from the remote exchange.
        Push to push data to the exchange.

        **[Required]** exchange: Name of the exchange the data should be pushed/pulled from.

        exchange_type: Type of the exchange for RabbitMq. Possible values (default: fanout): `["fanout", "topic"]`.

        url: Websocket gate URL. If not specified, `WEBSOCKET_GATE_URL` env var is used.

        robot_name: Robot, for which we are pushing/pulling data. If not specified, `ROBOT_NAME` env var is used.

        username: Username of user to log in into the exchange. If not specified, `RRF_USERNAME` env var is used.

        password: Password of user to log in into the exchange. If not specified, `RRF_PASSWORD` env var is used.

        rpc_user_type: an enum value of 'RpcUserType' for 'topic' type exchange.
        It sets a concrete way for work with personal messages.

        service_name: it is required only for rpc_user_type=='service'

        data_type: (For pull commands) Determines how the binary data from the exchange should be processed.
        The output from the WsRobotProcess to the queues will be of the according data_type.
        Possible values (default: "binary"): `["json", "binary", "bytes", "str", "string", "request", "bind_request"]`.

        ping_interval: Interval between pings that are being sent to the exchange in seconds. Default value: 1.0

        connection_timeout: Timeout for opening connection to the exchange in seconds. Default value: 1.5
    """

    # Functions to handle binary data coming from pull commands
    _PARSERS: T.Dict[str, T.Callable[[bytes], T.Any]] = {
        "json": lambda b: json.loads(b.decode("utf-8")),
        "str": lambda b: b.decode("utf-8"),
        "string": lambda b: b.decode("utf-8"),
        "bytes": lambda b: b,
        "binary": lambda b: b,
        "request": lambda b: Request.from_bson(b),
        "bind_request": lambda b: BindRequest.from_bson(b),
    }

    def __init__(self, *args, **kwargs):
        super(WsRobotProcess, self).__init__(*args, **kwargs)

        self._set_command_type(kwargs)
        self._set_exchange_params(kwargs)
        self._set_base_params_with_env(kwargs)
        self._set_rpc_params(kwargs)
        self._set_parser(kwargs)

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
                parsed: T.Any = self._parser(data)

                if self.rpc_user_type == RpcUserType.CLIENT:
                    self.respond_to(parsed)
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

            if self.rpc_user_type == RpcUserType.CLIENT:
                personal_message: Request = self.get_request()
                # todo what to do if service never exists ? for example server name is incorrect
                if not personal_message.service_name:
                    raise RuntimeError("Service name for personal message is absent.")

                data: bytes = personal_message.to_bson()

            elif self.rpc_user_type == RpcUserType.SERVICE:
                personal_bind_message: BindRequest = self.consume()
                data: bytes = personal_bind_message.to_bson()

            else:
                data: bytes = self.consume()

            if not isinstance(data, bytes):
                self.log.error(f"Trying to send non-binary data to push: {data}")
                raise RuntimeError("Data to send to ws should be binary")

            await ws.send(data)

    def _get_control_packet(self) -> str:
        extra_params = {}

        if self.command_type == WsCommandType.PULL:
            if self.rpc_user_type == RpcUserType.CLIENT:
                extra_params["exchange_bind_key"] = f"{self.robot_name}.*"

            elif self.rpc_user_type == RpcUserType.SERVICE:
                extra_params["exchange_bind_key"] = f"*.{self.service_name}"

        return WsRequest(
            command=self.command_type,
            robot_name=self.robot_name,
            username=self.username,
            password=self.password,
            exchange=self.exchange,
            exchange_type=self.exchange_type,
            **extra_params,
        ).json()

    @classmethod
    async def _silent_recv(self, ws):
        """Receive and drop incoming packets"""
        while True:
            await ws.recv()

    def _set_exchange_params(self, kwargs):
        self.exchange: str = kwargs["exchange"]

        self.exchange_type: str = kwargs.get("exchange_type", ExchangeType.fanout.value)
        if self.exchange_type not in (
            ExchangeType.topic.value,
            ExchangeType.fanout.value,
        ):
            raise RuntimeError("Unknown/disallowed exchange type.")

    def _set_command_type(self, kwargs: dict) -> None:
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

    def _set_parser(self, kwargs):
        # Data type handling for pull commands
        self.data_type: str = kwargs.get("data_type", "binary").lower()
        if self.data_type not in self._PARSERS:
            raise RuntimeError(
                f"Data type {self.data_type} is not in allowed types.\r\n"
                f"Please use one of following: {', '.join(self._PARSERS.keys())}"
            )

        self._parser = self._PARSERS[self.data_type]

    def _set_base_params_with_env(self, kwargs):
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

    def _set_rpc_params(self, kwargs):
        self.rpc_user_type: str = kwargs.get("rpc_user_type", RpcUserType.DEFAULT)

        incorrect_rpc_user_type = (
            self.exchange_type == ExchangeType.topic.value
            and self.rpc_user_type not in (RpcUserType.CLIENT, RpcUserType.SERVICE)
        )

        if incorrect_rpc_user_type:
            raise RuntimeError(
                "'Topic' exchange type requires correct 'rpc_user_type' value in config data !"
            )

        if self.rpc_user_type == RpcUserType.SERVICE:
            self.service_name = kwargs["service_name"]
