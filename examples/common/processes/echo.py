from rembrain_robot_framework import RobotProcess


class EchoProcess(RobotProcess):
    def run(self) -> None:
        while True:
            new_data = self.consume()
            self.log.info(f"Got data (type: {type(new_data)}): {new_data}")
