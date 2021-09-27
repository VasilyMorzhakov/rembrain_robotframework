import logging
from time import sleep

from rembrain_robot_framework import RobotProcess


class StubProcess(RobotProcess):
    """ It is just stub without any benefit work."""

    def run(self):
        logging.info(f"{self.__class__.__name__} started, name: {self.name}.")

        while True:
            sleep(20)
