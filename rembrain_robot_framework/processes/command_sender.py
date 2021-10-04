import json
import logging
from datetime import datetime, timezone

from rembrain_robot_framework import RobotProcess


# todo check it
class CommandSender(RobotProcess):
    def run(self):
        logging.info(f"{self.__class__.__name__} started, name: {self.name}.")
        #
        # request = WsRequest(
        #     command=WsCommandType.PUSH,
        #     exchange="commands",
        #     robot_name=os.environ["ROBOT_NAME"],
        #     username=os.environ["ROBOT_NAME"],
        #     password=os.environ["ROBOT_PASSWORD"],
        # )
        # ping_request: WsRequest = request.copy(update={"command": WsCommandType.PING})
        while True:
            message: str = self.consume()
            command: dict = json.loads(message)
            command["timestamp"] = datetime.now(timezone.utc).timestamp()

            logging.info(f"message to send: {command}")
            self.publish(message)
