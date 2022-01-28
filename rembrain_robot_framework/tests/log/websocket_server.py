import asyncio
import json
import typing as T
from multiprocessing import Value

import websockets


class WebsocketServer:
    def __init__(self, ws_port: int, dump_message: str, close_flag: Value):
        self.dump_message = dump_message
        self.ws_port = ws_port

        self.close_flag: Value = close_flag
        self.messages: T.List[T.Any] = []

    async def handle_msg(
            self, websocket: websockets.WebSocketServerProtocol, path: str
    ) -> None:
        async for message in websocket:
            if type(message) is bytes:
                message = message.decode("utf-8")

            if message == self.dump_message:
                await websocket.send(json.dumps(self.messages))
            else:
                self.messages.append(json.loads(message))
                await websocket.send(message)

    async def run(self) -> None:
        print(f"Starting websocket server on port {self.ws_port}")
        async with websockets.serve(self.handle_msg, "localhost", self.ws_port):
            while True:
                if self.close_flag.value:
                    print("Stopping websocket server")
                    return

                await asyncio.sleep(0.2)


def start_ws_server(close_flag: Value, ws_port: int, dump_message: str) -> None:
    server = WebsocketServer(ws_port, dump_message, close_flag)
    asyncio.run(server.run())
