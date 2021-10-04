import logging

from rembrain_robot_framework import RobotProcess

# todo check it
class StateProcess(RobotProcess):
    def run(self):
        logging.info(f"{self.__class__.__name__} started, name: {self.name}.")

        # ws_channel: Generator = self.ws_connect.pull(
        #     WsRequest(
        #         command=WsCommandType.PULL,
        #         exchange="state",
        #         robot_name=os.environ["ROBOT_NAME"],
        #         username=os.environ["ROBOT_NAME"],
        #         password=os.environ["ROBOT_PASSWORD"],
        #     )
        # )

        while True:
            status = self.consume()

            if status["state_machine"] == "NEED_ML":
                if not self.shared.ask_for_ml.value:
                    logging.info("ask_for_ml.value=True")

                self.shared.ask_for_ml.value = True
            else:
                self.shared.ask_for_ml.value = False

            for k, v in status.items():
                self.shared.status[k] = v
