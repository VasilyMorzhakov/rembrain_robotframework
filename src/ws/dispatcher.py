import os
import socket
import time
import typing as T
from threading import Thread
from traceback import format_exc

import websocket

from rembrain_robotframework.src.ws import WsCommandType, WsRequest


class WsDispatcher:
    def __init__(self):
        self.ws: T.Optional[websocket.WebSocket] = None
        self._reader: T.Optional[Thread] = None

    def open(self) -> None:
        if not self.ws or not self.ws.connected:
            self.ws = websocket.WebSocket()
            self.ws.connect(os.environ["WEBSOCKET_GATE_URL"])
            self._end_silent_reader()

    def close(self) -> None:
        try:
            if self.ws:
                self.ws.close()
        except Exception:
            print(f"WsDispatcher ERROR: ws CLOSE failed. Reason: {format_exc()}.")

        self.ws = None
        self._end_silent_reader()

    def pull(self, request: WsRequest) -> T.Generator[T.Union[str, bytes], None, None]:
        """
        Open socket, send 'PULL' command to websocket and receive data constantly.
        :param request - request body
        :return: generator with response data
        """
        while True:
            try:
                self.open()
                self.ws.send(request.json())

                while True:
                    if not self.ws.connected:
                        break

                    response: T.Union[str, bytes] = self.ws.recv()
                    if isinstance(response, bytes) or (isinstance(response, str) and response != WsCommandType.PING):
                        yield response

            except Exception:
                print(f"WsDispatcher ERROR: SEND '{WsCommandType.PULL}' command failed. Reason: {format_exc()}.")

            time.sleep(5)
            self.close()

    # todo refactor params
    def push(
            self, request: WsRequest, retry_times: T.Optional[int] = None, delay: T.Optional[int] = None
    ) -> T.Optional[T.Union[str, bytes]]:
        """
        Open socket and send 'PUSH' command to websocket.
        :param request - request body
        :param retry_times - repeats, if retry_times is None => infinite generator
        :param delay - (optional) sleep interval in seconds if it needs
        :return: ws response
        """
        repeats: T.Iterator = iter(int, 1) if retry_times is None else range(retry_times)
        for _ in repeats:
            try:
                self.open()
                self.ws.send(request.json())
                return self.ws.recv()

            except socket.error:
                self.close()
                if retry_times is None:
                    time.sleep(5.0)

            except Exception:
                print(f"WsDispatcher ERROR: Send '{WsCommandType.PUSH}' command failed. Reason: {format_exc()}.")
                self.close()

        # todo try to remove this code
        if delay:
            time.sleep(delay)

    def push_loop(
            self, request: WsRequest, data: T.Union[str, bytes] = b""
    ) -> T.Generator[T.Union[str, bytes], bytes, None]:
        """
        Open socket, send 'PUSH' command to websocket with auth data and then send data constantly.
        :param request - request body
        :param data - bytes/str data for request
        :return: ws response
        """

        while True:
            try:
                self.open()
                self.ws.send(request.json())
                self.ws.recv()
                # todo does it need ?
                self.ws.settimeout(1.0)

                self._start_silent_reader()
                while True:
                    if not data:
                        data = yield  # for first query (for next())

                    if isinstance(data, bytes):
                        self.ws.send_binary(data)
                        data = yield
                    elif isinstance(data, str):
                        self.ws.send(data)
                        data = yield
                    else:
                        raise Exception("Unknown type of data.")

            except Exception:
                print(f"WsDispatcher ERROR: SEND '{WsCommandType.PUSH_LOOP}' command failed. Reason: {format_exc()}.")
                self.close()
                time.sleep(2.0)

    def _start_silent_reader(self) -> None:
        self._reader = Thread(target=self._silent_recv, daemon=True)
        self._stop_reader = False
        self._reader.start()

    def _end_silent_reader(self) -> None:
        if self._reader:
            self._stop_reader = True
            self._reader.join()
            self._reader = None

    def _silent_recv(self) -> None:
        while not self._stop_reader:
            time.sleep(0.01)

            try:
                self.ws.recv()
            except:
                pass
