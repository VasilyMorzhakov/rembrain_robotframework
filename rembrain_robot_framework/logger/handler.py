import json
import logging
import os
import queue
import time
import typing as T
from threading import Thread
from traceback import format_exc

from python_logging_rabbitmq import FieldFilter

from rembrain_robot_framework.ws import WsRequest, WsCommandType, WsDispatcher


class LogHandler(logging.Handler):
    _RABBIT_EXCHANGE = os.environ.get("LOG_EXCHANGE", "logstash")
    _MAX_LOG_SIZE: int = 128
    _SEND_RETRIES = 2

    def __init__(self, fields: T.Optional[dict] = None, *args, **kwargs):
        super(LogHandler, self).__init__(*args, **kwargs)

        self.fields: dict = fields if isinstance(fields, dict) else {}
        if len(self.fields) > 0:
            self.addFilter(FieldFilter(self.fields, True))

        self.logs_queue = queue.Queue()

        self.last_ping_time = time.time()
        self.keep_alive_interval = 1.0

        # Disable logs so we don't lockup in a loop by accident
        self.ws_connect = WsDispatcher(propagate_log=False)
        Thread(target=self._send_to_ws, daemon=True).start()

    def emit(self, record: logging.LogRecord) -> None:
        try:
            formatted_record = self.format(record)
            binary_record = formatted_record.encode("utf-8")

            if self.logs_queue.qsize() < self._MAX_LOG_SIZE:
                self.logs_queue.put(binary_record)
            else:
                print(
                    "WARNING! Log queue overloaded, message wasn't delivered to websocket"
                )
        except Exception:
            print(
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

        loop = self.ws_connect.push_loop(request)
        next(loop)

        # Loop where we receive data from queue and pump it to the websocket
        while True:
            if self.logs_queue.qsize() > 0:
                msg = self.logs_queue.get()

                try:
                    for i in range(self._SEND_RETRIES):
                        loop.send(msg)
                        break
                    else:
                        raise RuntimeError(
                            f"Failed to deliver log message in {self._SEND_RETRIES} attempts"
                        )

                except Exception as e:
                    print("Exception in logging:", e)
                    time.sleep(5)
                    # Reinitialize the connection
                    self.ws_connect.close()
                    loop = self.ws_connect.push_loop(request)
                    next(loop)
            else:
                self._ping(loop)

    def _ping(self, push_loop: T.Generator) -> None:
        now: float = time.time()

        if now - self.last_ping_time >= self.keep_alive_interval:
            push_loop.send(json.dumps({"command": WsCommandType.PING}))
            self.last_ping_time = now

        time.sleep(0.001)
