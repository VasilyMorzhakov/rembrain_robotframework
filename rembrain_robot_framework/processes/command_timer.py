import json
import logging
from datetime import datetime, timezone

from rembrain_robot_framework import RobotProcess


# todo check it
# it was CommandSender
class CommandTimer(RobotProcess):
    def run(self):
        logging.info(f"{self.__class__.__name__} started, name: {self.name}.")
        while True:
            message: str = self.consume()
            command: dict = json.loads(message)
            command["timestamp"] = datetime.now(timezone.utc).timestamp()

            logging.info(f"message to send: {command}")
            self.publish(message)
