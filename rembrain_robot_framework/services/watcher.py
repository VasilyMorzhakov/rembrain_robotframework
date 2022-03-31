import asyncio
import os
import time
from multiprocessing import Queue

import websockets

from rembrain_robot_framework.ws import WsRequest, WsCommandType


class Watcher:
    EXCHANGE: str = "heartbeat"

    def __init__(self, queue: Queue) -> None:
        self.watcher_queue: Queue = queue

        self.ws_url = os.environ["WEBSOCKET_GATE_URL"]
        self.robot_name = os.environ["ROBOT_NAME"]
        self.username = os.environ["RRF_USERNAME"]
        self.password = os.environ["RRF_PASSWORD"]

    def notify(self) -> None:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self._send_to_ws())

    async def _send_to_ws(self):
        async for ws in websockets.connect(self.ws_url, open_timeout=1.5):
            try:
                if not self.watcher_queue.empty():
                    message = self.watcher_queue.get()

                    await ws.send(
                        WsRequest(
                            command=WsCommandType.PUSH,
                            exchange=self.EXCHANGE,
                            robot_name=self.robot_name,
                            username=self.username,
                            password=self.password,
                            message=message,
                        )
                    )
                await asyncio.sleep(0.1)

            except websockets.ConnectionClosedError as e:
                # todo how to log ?
                pass

            except (websockets.ConnectionClosed, websockets.ConnectionClosedOK):
                pass
