import numpy as np

from rembrain_robot_framework import RobotProcess


class DepthMixin(RobotProcess):
    """
    This process adds blank depth data to the image so it can then be used by the videopacker.
    """
    DEPTH: np.ndarray = np.zeros((256, 256, 3), np.uint8)

    def run(self):
        while True:
            self.publish((self.consume(), self.DEPTH))
