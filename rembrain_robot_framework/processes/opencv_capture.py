import time

import cv2

from rembrain_robot_framework import RobotProcess


class ImageCapture(RobotProcess):
    def __init__(self, *args, **kwargs):
        super(ImageCapture, self).__init__(*args, **kwargs)
        self.FPS_limit = kwargs.get("FPS_limit", 5)

    def run(self) -> None:
        vc_data = cv2.VideoCapture(0)
        while True:
            status, img = vc_data.read()
            if not status:
                break

            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            self.publish(img)
            time.sleep(1.0 / self.FPS_limit)
