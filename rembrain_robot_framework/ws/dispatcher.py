import logging
import os
import socket
import time
import typing as T
from threading import Thread
from traceback import format_exc

import stopit
import websocket

from rembrain_robot_framework.ws import WsCommandType, WsRequest


class WsDispatcher:
    CONNECTION_RETRIES = 3

    def __init__(self, propagate_log=True, proc_name=""):
        """
        :param propagate_log: whether to propagate the logs to the root logger
            if False, then a separate logger is created that just writes to the stderr
        """
        self.ws: T.Optional[websocket.WebSocket] = None
        self._reader: T.Optional[Thread] = None
        self.log = self._get_logger(propagate_log, proc_name)

    def open(self) -> None:
        if not self.ws or not self.ws.connected:
            self.log.info("Opening websocket connection")
            # Turn on SO_REUSEADDR so we can reuse hung sockets
            for i in range(self.CONNECTION_RETRIES):
                with stopit.ThreadingTimeout(0.5):
                    self.ws = websocket.WebSocket(sockopt=((socket.SOL_SOCKET, socket.SO_REUSEADDR, 1),))
                    self.ws.connect(os.environ["WEBSOCKET_GATE_URL"])
                    break
            else:
                err_msg = f"Method 'websocket.connect()' failed to connect after {self.CONNECTION_RETRIES} retries"
                self.log.error(err_msg)
                raise Exception(err_msg)

            # todo remove it ?
            self.ws.settimeout(10.0)
            self._end_silent_reader()

    def close(self) -> None:
        try:
            if self.ws:
                self.log.info("Closing websocket connection")
                self.ws.close()
        except Exception:
            self.log.error(f"WsDispatcher: ws close failed. Reason: {format_exc()}.")

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
                err_msg = f"WsDispatcher ERROR: SEND '{WsCommandType.PULL}' command failed. Reason: {format_exc()}."
                self.log.error(err_msg)

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
                self.log.error(f"WsDispatcher: Send '{WsCommandType.PUSH}' command failed. Reason: {format_exc()}.")
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
                        err_msg = (
                            f"Data type {type(data)} is invalid. "
                            f"You can only send either binary data, or string messages."
                        )
                        self.log.error(err_msg)
                        raise Exception(err_msg)

            except Exception:
                err_msg = f"WsDispatcher: Send '{WsCommandType.PUSH_LOOP}' command failed. Reason: {format_exc()}."
                self.log.error(err_msg)
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

    @staticmethod
    def _get_logger(propagate: bool, proc_name: str) -> logging.Logger:
        """
        Since WsDispatcher is used inside the websocket logger (See LogHandler class in `logger/handler.py`),
            we need to make sure we don't accidentally have an error loop where it breaks inside the logging framework.
        So to handle that, we turn off propagation to the root logger and create a simple StreamHandler logger.
        """
        pid = os.getpid()
        logger = logging.getLogger(f"{__name__} ({proc_name}:{pid})")
        logger.propagate = propagate

        # If this is not a propagating logger, then set it up with just a StreamHandler
        if not propagate:
            logger.setLevel(logging.INFO)

            for handler in logger.handlers:
                logger.removeHandler(handler)

            handler = logging.StreamHandler()
            formatter = logging.Formatter("%(levelname)s:%(name)s:%(message)s")
            handler.setFormatter(formatter)
            logger.addHandler(handler)

        return logger
