import time

from rembrain_robot_framework import RobotProcess


class YoloImageProcessor(RobotProcess):
    def __init__(self, *args, **kwargs):
        super(YoloImageProcessor, self).__init__(*args, **kwargs)

        device = kwargs.get("device", "cpu")

        # To prevent importing pytorch/etc in main process
        import yolov5
        self.model = yolov5.load("yolov5n.pt", device)

    def run(self) -> None:
        self.log.info("Hello from image processor!")

        while True:
            # Can call consume without args because it's the only queue for this process
            # The consume call is blocking so no need to poll
            image = self.consume()
            results = self.model(image)
            processed = results.render()[0]
            self.publish(processed)


