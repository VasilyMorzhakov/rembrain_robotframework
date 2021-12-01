import asyncio
import json
import logging
import os
import time
import typing as T

import websockets

from rembrain_robot_framework import RobotProcess
from rembrain_robot_framework.ws import WsCommandType, WsRequest


class WsRobotProcess(RobotProcess):

    # Functions to handle binary data coming from pull commands
    _data_type_parse_fns: T.Dict[str, T.Callable[[bytes], T.Any]] = {
        "json": lambda b: json.loads(b.decode("utf-8")),
        "str": lambda b: b.decode("utf-8"),
        "string": lambda b: b.decode("utf-8"),
        "bytes": lambda b: b,
        "binary": lambda b: b,
    }

    def __init__(self, *args, **kwargs):
        super(WsRobotProcess, self).__init__(*args, **kwargs)

        self.command_type: str = kwargs["command_type"]
        if self.command_type == WsCommandType.PUSH_LOOP:
            self.log.warning("Command type push_loop is now the same as push, change your config "
                             "since push_loop is deprecated")
            self.command_type = WsCommandType.PUSH
        if self.command_type not in WsCommandType.ALL_VALUES or self.command_type == WsCommandType.PING:
            raise RuntimeError("Unknown/disallowed command type")

        # TODO: delete this after push ACTUALLY becomes push-loop, and not the other way around
        if self.command_type == WsCommandType.PUSH:
            self.command_type = WsCommandType.PUSH_LOOP

        self.ws_url: str = kwargs.get("url", os.environ["WEBSOCKET_GATE_URL"])
        self.exchange: str = kwargs["exchange"]
        self.robot_name: str = kwargs.get("robot_name", os.environ["ROBOT_NAME"])
        self.username: str = kwargs.get("username", os.environ["RRF_USERNAME"])
        self.password: str = kwargs.get("password", os.environ["RRF_PASSWORD"])

        # Data type handling for pull commands
        self.data_type: str = kwargs.get("data_type", "binary").lower()
        if self.data_type not in self._data_type_parse_fns:
            raise RuntimeError(f"Data type {self.data_type} is not in allowed types."
                               f"\r\nPlease use one of following: {', '.join(self._data_type_parse_fns.keys())}")
        self._parse_fn = self._data_type_parse_fns[self.data_type]

        self.ping_interval = float(kwargs.get("ping_interval", 1.0))
        self.connection_timeout = float(kwargs.get("connection_timeout", 0.5))
        self._root_logger = logging.getLogger()

    def run(self) -> None:
        self.log.info(f"{self.__class__.__name__} started, name: {self.name}")

        if self.command_type == WsCommandType.PULL:
            asyncio.run(self._pull())
        elif self.command_type == WsCommandType.PUSH_LOOP:
            asyncio.run(self._push())

    async def _pull(self) -> None:
        async def _pull_fn(ws):
            while True:
                data = await ws.recv()
                self._publish_if_not_ping(data)
        await self._connect_ws(_pull_fn)

    def _publish_if_not_ping(self, data: T.Union[str, bytes]):
        """
        Handles incoming data from websocket
        If it's in binary, then it's a data packet that should be handled according to the process's data_type
        If it's a string, then it's a control packet
        """
        if type(data) is bytes:
            parsed = self._parse_fn(data)
            self.publish(parsed)
        # Strings are received only for control packets - right now it's only pings
        if type(data) is str:
            if data == WsCommandType.PING:
                return
            else:
                raise RuntimeError(f"Got non-ping string data from websocket, this shouldn't be happening"
                                   f"\r\nData: {data}")

    async def _push(self) -> None:
        async def _push_fn(ws):
            """
            This one has three long running function:
            - one for sending pings in keep_alive interval
            - one for consuming from queue and publishing
            - one for receiving and dropping any packages coming from the websocket
            """
            async def _ping():
                """Sends out ping packet ever self.ping_interval seconds"""
                control_packet = json.dumps({"command": WsCommandType.PING})
                # Wait for a bit for the regular connection to be established so we don't get dropped
                await asyncio.sleep(1.5)
                while True:
                    await ws.send(control_packet)
                    await asyncio.sleep(self.ping_interval)

            async def _get_then_send():
                """Gets data to send from the consume_queue (MUST be binary) and sends it to websocket"""
                while True:
                    if not self.is_empty():
                        self.log.debug("Getting data")
                        data = self.consume()
                        self.log.debug("Sending data")
                        if type(data) is not bytes:
                            raise RuntimeError("Data to send to ws should be binary")
                        await ws.send(data)
                    else:
                        await asyncio.sleep(0.01)

            async def _recv_sink():
                """Receive and drop incoming packets"""
                while True:
                    await ws.recv()

            await asyncio.gather(_ping(), _get_then_send(), _recv_sink())
        await self._connect_ws(_push_fn)

    async def _connect_ws(self, handler_fn) -> None:
        """
        Connects to the websocket, sends control packet
        then runs handler_fn that then uses the websocket however it needs
        """
        for i in range(5):
            try:
                ws = await asyncio.wait_for(websockets.connect(self.ws_url, logger=WebsocketsLogAdapter(self.log, {})),
                                            self.connection_timeout)
                self.log.info("Sending control packet")
                await ws.send(self.get_control_packet().json())
                # TODO: DELETE
                # After control packet sent, turn off debug logging
                if self._root_logger.level == logging.DEBUG:
                    self._root_logger.setLevel(logging.INFO)
                await handler_fn(ws)
                self.log.info("Handler function exited")
                await ws.close()
                return
            except asyncio.TimeoutError:
                self.log.warning(f"Couldn't connect to websocket server in {self.connection_timeout}")
                continue
            except websockets.ConnectionClosedError as e:
                msg = "Connection closed with error."
                if e.rcvd is not None:
                    msg += f" Reason: {e.rcvd.reason}"
                self.log.error(msg)
                return
            except websockets.ConnectionClosedOK as e:
                msg = "Connection closed."
                if e.rcvd is not None:
                    msg += f" Reason: {e.rcvd.reason}"
                self.log.info(msg)
                return
        else:
            self.log.error("Couldn't connect to websocket server in time after 5 attempts")

    def get_control_packet(self, command_type: T.Optional[WsCommandType] = None) -> WsRequest:
        if command_type is None:
            command_type = self.command_type
        return WsRequest(
            command=command_type,
            exchange=self.exchange,
            robot_name=self.robot_name,
            username=self.username,
            password=self.password
        )


class WebsocketsLogAdapter(logging.LoggerAdapter):
    def process(self, msg, kwargs):
        """
        Websockets adds its own LoggingAdapter that adds an unpicklable websocket class,
        We have to get rid of it so we can pass log messages accross processes
        """
        if "websocket" in kwargs["extra"]:
            del(kwargs["extra"]["websocket"])
        return msg, kwargs
