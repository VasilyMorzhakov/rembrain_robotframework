from rembrain_robot_framework import RobotProcess


class StateProcess(RobotProcess):
    def run(self):
        self.log.info(f"{self.__class__.__name__} started, name: {self.name}.")

        while True:
            status = self.consume()
            if status["state_machine"] == "NEED_ML" and not self.shared.ask_for_ml.value:
                self.log.info("ask_for_ml.value=True")

            self.shared.ask_for_ml.value = (status["state_machine"] == "NEED_ML")
            for k, v in status.items():
                self.shared.status[k] = v
