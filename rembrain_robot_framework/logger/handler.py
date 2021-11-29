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

    def __init__(self, fields: T.Optional[dict] = None, *args, **kwargs):
        super(LogHandler, self).__init__(*args, **kwargs)

        self.fields: dict = fields if isinstance(fields, dict) else {}
        if len(self.fields) > 0:
            self.addFilter(FieldFilter(self.fields, True))

        self.logs_queue = queue.Queue()

        # Disable logs so we don't lockup in a loop by accident
        self.ws_connect = WsDispatcher(propagate_log=False)
        Thread(target=self._send_to_ws, daemon=True).start()

    def emit(self, record: logging.LogRecord) -> None:
        try:
            formatted_record = self._get_formatted_record(record)

            if "RRF_USERNAME" in os.environ:
                username: str = os.environ["RRF_USERNAME"]
                password: str = os.environ["RRF_PASSWORD"]
            else:
                username: str = os.environ["ML_NAME"]
                password: str = os.environ["ML_PASSWORD"]

            request = WsRequest(
                command=WsCommandType.PUSH,
                exchange=self._RABBIT_EXCHANGE,
                robot_name="",
                username=username,
                password=password,
                message=formatted_record,
            )

            if self.logs_queue.qsize() < self._MAX_LOG_SIZE:
                self.logs_queue.put(request)

        except Exception:
            print("Attention: logger exception - record was not written! Reason:", format_exc())

    def _get_formatted_record(self, record: logging.LogRecord) -> T.Any:
        formatted_record: str = self.format(record)

        try:
            formatted_record = json.loads(formatted_record)
        except (UnicodeDecodeError, json.JSONDecodeError):
            pass

        return formatted_record

    def _send_to_ws(self) -> None:
        while True:
            try:
                if self.logs_queue.qsize() > 0:
                    self.ws_connect.open()
                    request: WsRequest = self.logs_queue.get()
                    self.ws_connect.push(request, retry_times=2, delay=5)

            except Exception as e:
                print("Exception in logging:", e)
                time.sleep(5)
                self.ws_connect.close()

            time.sleep(0.1)
