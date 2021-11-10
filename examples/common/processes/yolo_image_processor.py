from rembrain_robot_framework import RobotProcess


class YoloImageProcessor(RobotProcess):
    def __init__(self, *args, **kwargs):
        super(YoloImageProcessor, self).__init__(*args, **kwargs)

        # To prevent importing pytorch/etc in main process
        import yolov5
        device = kwargs.get("device", "cpu")
        self.model = yolov5.load("yolov5n.pt", device)
        self.frame_counter = 0

    def run(self) -> None:
        self.log.info("Hello from image processor!")

        while True:
            # Can call consume without args because it's the only queue for this process
            # The consume call is blocking so no need to poll
            image = self.consume()

            # In external example processor actually consumes a tuple of (image, depth), so check for that
            depth_data = None
            if type(image) is tuple:
                image = image[0]
                depth_data = image[1]

            results = self.model(image)
            processed = results.render()[0]

            self.frame_counter += 1
            if self.frame_counter % 30 == 0:
                self.log.info(f"{self.frame_counter} frames processed")

            # Pack depth data back in
            if depth_data is not None:
                processed = (processed, depth_data)

            self.publish(processed)
