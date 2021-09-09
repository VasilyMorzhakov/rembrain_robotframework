import json
import logging
import os
import time
from datetime import datetime, timezone

from rembrain_robotframework import RobotProcess
from rembrain_robotframework.src.ws.command_type import WsCommandType
from rembrain_robotframework.src.ws.dispatcher import WsDispatcher
from rembrain_robotframework.src.ws.request import WsRequest


class CommandSender(RobotProcess):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ws_connect = WsDispatcher()

    def run(self):
        logging.info(f"Started rabbit sensor sender process, name: {self.name}.")

        request = WsRequest(
            command=WsCommandType.PUSH,
            exchange="commands",
            robot_name=os.environ["ROBOT_NAME"],
            username=os.environ["ROBOT_NAME"],
            password=os.environ["ROBOT_PASSWORD"],
        )
        ping_request: WsRequest = request.copy(update={"command": WsCommandType.PING})

        while True:
            if self.consume_queues["ml_to_robot"].empty():
                time.sleep(0.01)
                self.ws_connect.push(ping_request)
            else:
                message: str = self.consume(queue_name="ml_to_robot")
                command: dict = json.loads(message)
                command["timestamp"] = datetime.now(timezone.utc).timestamp()

                logging.info(f"message to send: {command}")
                request.message = command
                self.ws_connect.push(request)
