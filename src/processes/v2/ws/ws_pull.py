import logging
import typing as T

from src.processes.v2.ws.ws_base import WsBaseProcess
from rembrain_robotframework.src.ws import WsCommandType


class WsPullProcess(WsBaseProcess):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.is_decode: bool = kwargs.get('is_decode', False)

    def ws_type(self):
        return WsCommandType.PULL

    def run(self):
        logging.info(f"{self.__class__.__name__} started, name: {self.name}.")
        ws_channel: T.Generator = self.ws_connect.pull(self.ws_request())

        while True:
            response_data: T.Union[str, bytes] = next(ws_channel)
            if self.is_decode:
                response_data = response_data.decode(encoding="utf-8")

            self.queue.put(response_data)
