import os
import typing as T

import pika
from pika import BlockingConnection

from rembrain_robot_framework.ws import WsDispatcher, WsRequest, WsCommandType


class Watcher:
    EXCHANGE = "heartbeat"

    def __init__(self, in_cluster: bool):
        self._in_cluster: bool = in_cluster
        self._connect: T.Union[BlockingConnection, WsDispatcher, None] = None

    def notify(self, message: str) -> None:
        self._notify_rabbit(message)

    def _notify_rabbit(self, message: str) -> None:
        if self._in_cluster:
            self._rabbit_connect()
            channel = self._connect.channel()
            channel.basic_publish(exchange=self.EXCHANGE, routing_key="", body=message.encode())
            channel.close()
        else:
            self._ws_connect()
            self._connect.push(WsRequest(
                command=WsCommandType.PUSH,
                exchange=self.EXCHANGE,
                robot_name=os.environ["ROBOT_NAME"],
                username=os.environ["ROBOT_NAME"],
                password=os.environ["ROBOT_PASSWORD"],
            ))

    def _rabbit_connect(self):
        if self._connect:
            return

        self._connect = BlockingConnection(pika.ConnectionParameters(host="rabbitmq"))

    def _ws_connect(self):
        if self._connect:
            return

        self._connect = WsDispatcher()
