import logging
import os

from rembrain_robot_framework.ws import WsDispatcher, WsRequest, WsCommandType


class Watcher:
    EXCHANGE = "heartbeat"

    def __init__(self, in_cluster: bool) -> None:
        self._in_cluster: bool = in_cluster
        self._connect = WsDispatcher()
        self.log = logging.getLogger("RobotDispatcher")

    def notify(self, message: str) -> None:
        if self._in_cluster:
            self.log.warning("Heartbeat may be used only out of cluster processes.")
            return

        self._send_to_ws(message)

    def _send_to_ws(self, message: str) -> None:
        self._connect.push(WsRequest(
            command=WsCommandType.PUSH,
            exchange=self.EXCHANGE,
            robot_name=os.environ["ROBOT_NAME"], # todo how to pass params
            username=os.environ["RRF_USERNAME"],
            password=os.environ["RRF_PASSWORD"],
            message=message
        ))
