import os
import time
from multiprocessing import Queue

from rembrain_robot_framework.ws import WsDispatcher, WsRequest, WsCommandType


class Watcher:
    EXCHANGE: str = "heartbeat"

    def __init__(self, queue: Queue) -> None:
        self._connect = WsDispatcher()
        self.watcher_queue: Queue = queue

    def notify(self) -> None:
        while True:
            if self.watcher_queue.qsize() > 0:
                self._send_to_ws(self.watcher_queue.get())

            time.sleep(0.1)

    def _send_to_ws(self, message: str) -> None:
        self._connect.push(
            WsRequest(
                command=WsCommandType.PUSH,
                exchange=self.EXCHANGE,
                robot_name=os.environ["ROBOT_NAME"],
                username=os.environ["RRF_USERNAME"],
                password=os.environ["RRF_PASSWORD"],
                message=message,
            )
        )
