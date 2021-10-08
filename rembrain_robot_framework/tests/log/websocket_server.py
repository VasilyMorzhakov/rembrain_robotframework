import asyncio
import json
import typing as T
from multiprocessing import Value
from threading import Thread

import websockets


class WebsocketServer:
    GET_DATA_TEXT = "get_data"

    def __init__(self, ws_port: str):
        self.ws_port: str = ws_port
        self.exec_thread: T.Optional[Thread] = None
        self.close_flag: T.Optional[Value] = None
        self.messages: T.List[T.Any] = []

    async def handle_msg(self, websocket: websockets.WebSocketServerProtocol, path: str) -> None:
        async for message in websocket:
            if message == self.GET_DATA_TEXT:
                await websocket.send(json.dumps(self.messages))
            else:
                self.messages.append(json.loads(message))

            await websocket.send(message)

    async def run(self) -> None:
        print("Starting websocket server")
        async with websockets.serve(self.handle_msg, "127.0.0.1", self.ws_port):
            if self.close_flag.value:
                return

            await asyncio.Future()

    async def check_close(self) -> None:
        while True:
            if self.close_flag.value:
                break

            await asyncio.sleep(1.0)

    def start(self, close_flag: Value) -> None:
        loop = asyncio.new_event_loop()
        self.close_flag = close_flag

        check_task = loop.create_task(self.check_close())
        loop.create_task(self.run())
        loop.run_until_complete(check_task)