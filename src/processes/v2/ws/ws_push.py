import logging

from rembrain_robotframework.src.ws import WsCommandType
from src.processes.v2.ws.ws_base import WsBaseProcess


class WsPushProcess(WsBaseProcess):
    def ws_type(self) -> str:
        return WsCommandType.PUSH

    def run(self):
        logging.info(f"{self.__class__.__name__} started, name: {self.name}.")
        request = self.ws_request()

        while True:
            request.message = self.queue.get()
            self.ws_connect.push(request)
