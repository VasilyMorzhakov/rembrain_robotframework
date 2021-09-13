import logging

from rembrain_robotframework import RobotProcess


# todo it does not need for this realization ?
class SensorSender(RobotProcess):
    """ It sends messages (like current robot position) to the server."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "to_play" in self.publish_queues:
            self.publish("online", queue_name="to_play")

    def run(self) -> None:
        logging.info(f"{self.__class__.__name__} started, name: {self.name}.")
