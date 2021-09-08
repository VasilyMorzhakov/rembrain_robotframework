import logging
import os
import time
import typing as T

import keyboard
import pyaudio

from robot_framework import RobotProcess
from robot_framework.src.ws.command_type import WsCommandType
from robot_framework.src.ws.dispatcher import WsDispatcher
from robot_framework.src.ws.request import WsRequest


class AudioSender(RobotProcess):
    """ It receives commands from server and sends them to the robot (supervisor). """

    def __init__(self, exchange_name: str, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.ws_connect = WsDispatcher()
        self.audio = pyaudio.PyAudio()
        self.audio_stream: T.Optional[pyaudio.Stream] = None

        self.time: int = 0
        self.exchange_name: str = exchange_name
        self.push_to_talk: bool = kwargs.get("push_to_talk", False)
        self.device: int = kwargs.get("device", 0)

    def run(self) -> None:
        logging.info(f"{self.__class__.__name__} started, name: {self.name}.")

        ws_channel = self.ws_connect.push_loop(
            WsRequest(
                command=WsCommandType.PUSH_LOOP,
                exchange=self.exchange_name,
                robot_name=os.environ["ROBOT_NAME"],
                username=os.environ["ROBOT_NAME"],
                password=os.environ["ROBOT_PASSWORD"],
            )
        )
        next(ws_channel)

        def callback(data: T.Any, *args) -> T.Tuple[None, int]:
            play = False

            if self.push_to_talk:
                if keyboard.is_pressed("`"):
                    play = True
            else:
                play = True

            self.time += 1

            if play and not hasattr(self.shared, "send_audio") or self.shared.send_audio.value:
                ws_channel.send(data)

            return None, pyaudio.paContinue

        self.audio_stream: pyaudio.Stream = self.audio.open(
            format=pyaudio.paFloat32,
            channels=1,
            rate=32000,
            input=True,
            frames_per_buffer=2048,
            stream_callback=callback,
            input_device_index=self.device,
        )

        while True:
            time.sleep(10)

    def close_objects(self) -> None:
        if self.audio_stream:
            self.audio_stream.stop_stream()
            self.audio_stream.close()
