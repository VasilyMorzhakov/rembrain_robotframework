import os
import time
import typing as T
from threading import Thread
from traceback import format_exc

import pika
from pika import BlockingConnection

from rembrain_robot_framework import RobotDispatcher
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
            # directly to rabbit
            self._send_to_rabbit(message)
        else:
            # through sockets
            self._send_to_ws(message)

    def _send_to_rabbit(self, message: str) -> None:
        for _ in range(5):
            try:
                self._rabbit_connect()
                channel = self._connect.channel()
                channel.basic_publish(exchange=self.EXCHANGE, routing_key="", body=message.encode())
                channel.close()
            except Exception:
                # todo add log
                # log.error(f"Watcher: RabbitMq connect error. Reason: {format_exc()}")
                self._connect = None
                time.sleep(2)

    def _send_to_ws(self, message: str) -> None:
        self._ws_connect()
        self._connect.push(WsRequest(
            command=WsCommandType.PUSH,
            exchange=self.EXCHANGE,
            robot_name=os.environ["ROBOT_NAME"],
            username=os.environ["ROBOT_NAME"],
            password=os.environ["ROBOT_PASSWORD"],
            message=message
        ))

    def _rabbit_connect(self):
        if self._connect:
            return

        if "RABBIT_ADDRESS" not in os.environ:
            raise Exception("Watcher: Env vars 'RABBIT_ADDRESS' does not exist.")

        auth_data, host = os.environ["RABBIT_ADDRESS"].split("@")
        user, password = auth_data.replace("amqp://", "").split(":")
        credentials = pika.PlainCredentials(user, password)
        connection_params = pika.ConnectionParameters(host=host[:-1], credentials=credentials)
        self._connect = pika.BlockingConnection(connection_params)

    def _ws_connect(self):
        if self._connect:
            return

        self._connect = WsDispatcher()
