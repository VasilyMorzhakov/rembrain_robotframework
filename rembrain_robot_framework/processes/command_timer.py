import json
from datetime import datetime, timezone

from rembrain_robot_framework import RobotProcess


class CommandTimer(RobotProcess):
    def run(self):
        self.log.info(f"{self.__class__.__name__} started, name: {self.name}.")

        while True:
            message: str = self.consume()
            command: dict = json.loads(message)
            command["timestamp"] = datetime.now(timezone.utc).timestamp()

            self.log.info(f"message to send: {command}")
            self.publish(json.dumps(command).encode('utf-8'))
