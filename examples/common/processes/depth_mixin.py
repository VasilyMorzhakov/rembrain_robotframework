import numpy as np

from rembrain_robot_framework import RobotProcess


class DepthMixin(RobotProcess):
    """
    This process adds blank depth data to the image so it can then be used by the videopacker
    """

    def __init__(self, *args, **kwargs):
        super(DepthMixin, self).__init__(*args, **kwargs)
        self.depth_value: np.ndarray = np.zeros((256, 256, 3), np.uint8)

    def run(self):
        while True:
            self.publish((self.consume(), self.depth_value))
