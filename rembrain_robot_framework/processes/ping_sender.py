import logging
import os
import subprocess
import time

from rembrain_robot_framework import RobotProcess
from rembrain_robot_framework.ws import WsCommandType, WsDispatcher, WsRequest


class PingSender(RobotProcess):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ws_connect = WsDispatcher()

        # get container ID - it's assumed, that we're in a docker container
        try:
            docker_s = subprocess.check_output(["cat", "/proc/1/cpuset"]).decode("utf-8")
            self.container_id = docker_s[8: 8 + 12]
        except Exception as e:
            self.container_id = "ERROR"
            logging.error(e, exc_info=True)

    def run(self):
        logging.info(f"Started pinger process, name: {self.name}.")
        request = WsRequest(
            command=WsCommandType.PUSH,
            exchange="processor_ping_sender",
            robot_name=os.environ["ROBOT_NAME"],
            username=os.environ["ROBOT_NAME"],
            password=os.environ["ROBOT_PASSWORD"],
        )

        while True:
            processor_info = {
                "associated_robot": os.environ["ROBOT_NAME"],
                "template_type": os.environ["TEMPLATE_TYPE"],
                "active": self.shared.processor_active.value,
                "id": self.container_id
            }
            request.message = processor_info
            self.ws_connect.push(request)
            time.sleep(1)
