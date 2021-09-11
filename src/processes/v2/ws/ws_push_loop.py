import logging
import typing as T

from rembrain_robotframework.src.ws.command_type import WsCommandType
from src.processes.v2.ws.ws_base import WsBaseProcess


class WsPushLoopProcess(WsBaseProcess):
    def ws_type(self) -> str:
        return WsCommandType.PUSH_LOOP

    def run(self):
        logging.info(f"{self.__class__.__name__} started, name: {self.name}.")
        push_loop: T.Generator = self.ws_connect.push_loop(self.ws_request())
        next(push_loop)

        while True:
            push_loop.send(self.queue.get())
