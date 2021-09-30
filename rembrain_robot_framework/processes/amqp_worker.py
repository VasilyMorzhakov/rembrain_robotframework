import logging

from rembrain_robot_framework import RobotProcess


# it was AmqpReceiver!!!!!!
# todo check it
class AmqpWorker(RobotProcess):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.shared.update_config.value = False

    def run(self):
        logging.info(f"{self.__class__.__name__} started, name: {self.name}.")
        while True:
            # it must be decoded!
            command = self.consume()
            if command["message"] == "update_config":
                self.shared.update_config.value = True
            else:
                logging.warning(f"Unprocessed command received: {command}")
