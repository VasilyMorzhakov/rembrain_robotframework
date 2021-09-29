import logging

from rembrain_robot_framework import RobotProcess


# todo rename to AmqpWorker!
# todo check it
class AmqpReceiver(RobotProcess):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.shared.update_config.value = False

    def run(self):
        logging.info(f"{self.__class__.__name__} started, name: {self.name}.")
        # ws_channel: Generator = self.ws_connect.pull(WsRequest(
        #     command=WsCommandType.PULL,
        #     exchange="processor_commands",
        #     robot_name=os.environ["ROBOT_NAME"],
        #     username=os.environ["ROBOT_NAME"],
        #     password=os.environ["ROBOT_PASSWORD"],
        # ))

        while True:
            # command = json.loads(response_data.decode(encoding="utf-8"))
            # it must be decoded!
            command = self.consume()
            if command["message"] == "update_config":
                self.shared.update_config.value = True
            else:
                logging.warning(f"Unprocessed command received: {command}")
