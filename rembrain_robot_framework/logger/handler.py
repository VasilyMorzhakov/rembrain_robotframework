import asyncio
import json
import logging
import os
import queue
import typing as T
from threading import Thread
from traceback import format_exc

import websockets
from python_logging_rabbitmq import FieldFilter

from rembrain_robot_framework.ws import (
    WsRequest,
    WsCommandType,
    WsLogAdapter,
)


class LogHandler(logging.Handler):
    _RABBIT_EXCHANGE = os.environ.get("LOG_EXCHANGE", "logstash")
    _MAX_LOG_SIZE: int = 128
    _SEND_RETRIES = 2

    def __init__(self, fields: T.Optional[dict] = None, *args, **kwargs):
        super(LogHandler, self).__init__(*args, **kwargs)

        # Setting up the inner logger (only to stderr)
        self.log = logging.getLogger(__name__)

        # Turn off propagation so we don't write to ourselves
        self.log.propagate = False
        for handler in self.log.handlers:
            self.log.removeHandler(handler)

        handler = logging.StreamHandler()
        formatter = logging.Formatter("%(levelname)s:%(name)s:%(message)s")
        handler.setFormatter(formatter)
        self.log.addHandler(handler)

        self.logs_queue = queue.Queue(maxsize=200)
        self.fields: dict = fields if isinstance(fields, dict) else {}
        if len(self.fields) > 0:
            self.addFilter(FieldFilter(self.fields, True))

        # Start a new thread where we send the log records to the websocket
        Thread(target=self._send_to_ws, daemon=True).start()

    def emit(self, record: logging.LogRecord) -> None:
        try:
            formatted_record = self.format(record)
            binary_record = formatted_record.encode("utf-8")

            if self.logs_queue.qsize() < self._MAX_LOG_SIZE:
                self.logs_queue.put(binary_record)
            else:
                self.log.warning(
                    "WARNING! Log queue overloaded, message wasn't delivered to websocket"
                )
        except Exception:
            self.log.error(
                "Attention: logger exception - record was not written! Reason:",
                format_exc(),
            )

    def _send_to_ws(self) -> None:
        # Init connection
        robot_name = os.environ.get("ROBOT_NAME", "")
        if "RRF_PASSWORD" in os.environ:
            username: str = os.environ["RRF_USERNAME"]
            password: str = os.environ["RRF_PASSWORD"]
        else:
            username: str = os.environ["ML_NAME"]
            password: str = os.environ["ML_PASSWORD"]

        request = WsRequest(
            command=WsCommandType.PUSH_LOOP,
            exchange=self._RABBIT_EXCHANGE,
            robot_name=robot_name,
            username=username,
            password=password,
        )
        loop = asyncio.new_event_loop()
        loop.run_until_complete(self._connect_ws(request))

    async def _connect_ws(self, control_packet: WsRequest) -> None:
        """
        Connects to the websocket, sends control packet then starts the push loop
        This always runs in an infinite loop and restarts if cancels
        """

        async for ws in websockets.connect(
            os.environ["WEBSOCKET_GATE_URL"],
            logger=WsLogAdapter(self.log, {}),
            open_timeout=1.5,
        ):
            try:
                self.log.info("Sending control packet")
                await ws.send(control_packet.json())
                await asyncio.gather(self._ping(ws), self._send_log_record(ws))
                continue
            except websockets.ConnectionClosedError as e:
                msg = "Connection closed with error."
                if e.rcvd is not None:
                    msg += f" Reason: {e.rcvd.reason}"

                self.log.error(msg)
                continue

            except websockets.ConnectionClosedOK as e:
                msg = "Connection closed."
                if e.rcvd is not None:
                    msg += f" Reason: {e.rcvd.reason}"

                self.log.info(msg)
                continue

    @staticmethod
    async def _ping(ws):
        control_packet = json.dumps({"command": WsCommandType.PING})

        while True:
            await asyncio.sleep(1.0)
            await ws.send(control_packet)

    async def _send_log_record(self, ws):
        while True:
            if self.logs_queue.qsize() > 0:
                msg = self.logs_queue.get()
                await ws.send(msg)
            else:
                await asyncio.sleep(0.01)
