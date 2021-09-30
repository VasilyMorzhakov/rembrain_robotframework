import json
import logging
import time
from datetime import datetime, timezone

from rembrain_robot_framework import RobotProcess
from rembrain_robot_framework.ws import WsCommandType


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
            # todo remove condition?
            if self.consume_queues["ml_to_robot"].empty():
                time.sleep(0.01)
                self.publish({"command": WsCommandType.PING})
            else:
                message: str = self.consume()
                command: dict = json.loads(message)
                command["timestamp"] = datetime.now(timezone.utc).timestamp()

                logging.info(f"message to send: {command}")
                self.publish(message)
