import asyncio
from multiprocessing import Value
from threading import Thread

import websockets
import json


class WebsocketServer:

    GET_DATA_TEXT = "get_data"

    def __init__(self, ws_port: str):
        self.ws_port = ws_port
        self.exec_thread: Thread = None
        self.close_flag: Value = None
        self.messages = []

    async def handle_msg(self, websocket, path):
        async for message in websocket:
            if message == self.GET_DATA_TEXT:
                await websocket.send(json.dumps(self.messages))
            else:
                self.messages.append(json.loads(message))
            await websocket.send(message)

    async def run(self):
        print("Starting websocket server")
        async with websockets.serve(self.handle_msg, "127.0.0.1", self.ws_port):
            if self.close_flag.value:
                return
            await asyncio.Future()

    async def check_close(self):
        while True:
            if self.close_flag.value:
                break
            await asyncio.sleep(1.0)

    def start(self, close_flag: Value):
        loop = asyncio.new_event_loop()
        self.close_flag = close_flag
        check_task = loop.create_task(self.check_close())
        server_task = loop.create_task(self.run())
        loop.run_until_complete(check_task)
