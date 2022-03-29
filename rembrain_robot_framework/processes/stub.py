from time import sleep

from rembrain_robot_framework import RobotProcess


class StubProcess(RobotProcess):
    """
    Stub process that doesn't do any work.
    Can be used as e.g. a sink for queues that are not used while debugging.
    """

    SLEEP_TIME = 10

    def __init__(self, eternal_loop: bool = True, *args, **kwargs):
        super(StubProcess, self).__init__(*args, **kwargs)
        self.eternal_loop = eternal_loop

    def run(self):
        self.log.info(f"{self.__class__.__name__} started, name: {self.name}.")

        sleep(self.SLEEP_TIME)
        while self.eternal_loop:
            sleep(self.SLEEP_TIME)
