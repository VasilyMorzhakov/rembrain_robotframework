import time
import cv2
import os

from rembrain_robot_framework import RobotProcess


class ImageCapture(RobotProcess):
    def __init__(self, *args, **kwargs):
        super(ImageCapture, self).__init__(*args, **kwargs)
        self.FPS_limit = kwargs.get("FPS_limit", 5)

    def run(self) -> None:
        cap = cv2.VideoCapture(0)
        while True:
            ret, img = cap.read()
            if not ret:
                break
            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            self.publish(img)
            time.sleep(1.0 / self.FPS_limit)
