import time

from rembrain_robot_framework import RobotProcess


class YoloImageProcessor(RobotProcess):
    def __init__(self, *args, **kwargs):
        super(YoloImageProcessor, self).__init__(*args, **kwargs)

        # To prevent importing pytorch/etc in main process
        import yolov5
        self.model = yolov5.load("yolov5n.pt")

    def run(self) -> None:
        self.log.info("Hello from image processor!")

        while True:
            if not self.consume_queues["image_orig"].empty():
                # Can call consume without args because it's the only queue for this process
                image = self.consume()
                results = self.model(image)
                processed = results.render()[0]
                self.publish(processed)

            time.sleep(0.01)

