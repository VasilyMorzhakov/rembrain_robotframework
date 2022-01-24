import os
import time

import cv2

from rembrain_robot_framework import RobotProcess


class ImageCapture(RobotProcess):
    FPS = 5

    def __init__(self, *args, **kwargs):
        super(ImageCapture, self).__init__(*args, **kwargs)

        image_path = os.path.join(os.path.dirname(__file__), "..", "static", "dog.jpg")
        self.image = cv2.imread(image_path)
        self.image = cv2.cvtColor(self.image, cv2.COLOR_BGR2RGB)
        self.frame_number = 0

    def run(self) -> None:
        while True:
            self.frame_number += 1

            img = self.image.copy()
            img = cv2.putText(
                img,
                str(self.frame_number),
                (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                (255, 255, 255),
                2,
                cv2.LINE_AA,
            )

            self.publish(img)

            if self.frame_number % 30 == 0:
                self.log.info("Sending heartbeat")
                self.heartbeat(f"Hello! Sent {self.frame_number} messages")

            time.sleep(1.0 / self.FPS)
