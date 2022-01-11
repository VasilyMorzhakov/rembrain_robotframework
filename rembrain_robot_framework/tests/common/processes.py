import time
import typing as T

import numpy as np

from rembrain_robot_framework import RobotProcess
from rembrain_robot_framework.models.named_message import NamedMessage


class P1(RobotProcess):
    def run(self) -> None:
        self.publish("hi")
        self.log.info(self.name + " hi sent")


class P2(RobotProcess):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.to_expect = kwargs.get("expect", "hi")

    def run(self) -> None:
        start_time: float = time.time()

        while time.time() - start_time < 2:
            record: str = self.consume()
            if record == self.to_expect:
                with self.shared.hi_lock:
                    self.shared.hi_received.value += 1
                self.log.info(f"{self.name} {record} received")


class P3(RobotProcess):
    def run(self) -> None:
        rec: str = self.consume("messages1")
        if rec == "hi":
            with self.shared.hi_lock:
                self.shared.hi_received.value += 1
            self.log.info(self.name + " hi received")

        rec = self.consume("messages2")
        if rec == "hi":
            with self.shared.hi_lock:
                self.shared.hi_received.value += 1
            self.log.info(self.name + " hi received")


class P4(RobotProcess):
    def run(self) -> None:
        self.publish(queue_name="messages1", message="hi1")
        self.publish(queue_name="messages2", message="hi2")
        self.log.info(self.name + " hi sent")


class AP1(RobotProcess):
    def __init__(self, *args, **kwargs):
        super(AP1, self).__init__(*args, **kwargs)
        self.custom_queue_name = kwargs.get("custom_queue_name")
        self.custom_test_message = kwargs.get("custom_test_message")

    def run(self) -> None:
        self.publish(
            queue_name=self.custom_queue_name, message=self.custom_test_message
        )
        self.log.info(self.name + " published message successfully.")


class AP2(RobotProcess):
    def __init__(self, *args, **kwargs):
        super(AP2, self).__init__(*args, **kwargs)
        self.custom_queue_name = kwargs.get("custom_queue_name")
        self.custom_test_message = kwargs.get("custom_test_message")

    def run(self) -> None:
        message: T.Any = self.consume(queue_name=self.custom_queue_name)
        self.log.info(f"{self.name} get message: {message}")
        self.shared.success.value = message == self.custom_test_message


class VideoSender(RobotProcess):
    def run(self) -> None:
        z = np.zeros((212, 256, 3))
        for _ in range(4000):
            z[:] = np.random.random((212, 256, 3))
            self.publish(z)


class VideoConsumer(RobotProcess):
    def run(self) -> None:
        self.shared.frames_processed.value = 0
        for _ in range(4000):
            record: str = self.consume()
            assert record.shape == (212, 256, 3)
            self.shared.frames_processed.value += 1


class SysP1(RobotProcess):
    TEST_MESSAGE = "REQUEST_TEST_MESSAGE"

    def run(self) -> None:
        personal_id: str = self.publish_request(
            self.TEST_MESSAGE, queue_name="messages"
        )
        self.shared.response["id"] = personal_id
        self.shared.response["data"] = self.wait_response(request_id=personal_id)


class SysP2(RobotProcess):
    TEST_MESSAGE = "RESPONSE_TEST_MESSAGE"

    def run(self) -> None:
        time.sleep(2)
        named_message: NamedMessage = self.consume(queue_name="messages")

        self.shared.request["id"] = named_message.id
        self.shared.request["data"] = named_message.data
        self.respond_to(named_message, data=self.TEST_MESSAGE)


class QueueSizeP1(RobotProcess):
    def run(self) -> None:
        while True:
            queue_name = self.shared.publish_message.get("queue_name")
            if queue_name:
                repeats = self.shared.publish_message.get("repeats")

                for _ in range(repeats):
                    self.publish("test", queue_name=queue_name)

                self.shared.publish_message["queue_name"] = None

            time.sleep(0.5)
            if self.shared.finish_load.value:
                break


class QueueSizeP2(RobotProcess):
    def run(self) -> None:
        while True:
            queue_name = self.shared.consume_message.get("queue_name")
            if queue_name:
                repeats = self.shared.consume_message.get("repeats")

                for _ in range(repeats):
                    self.consume(queue_name=queue_name)

                self.shared.consume_message["queue_name"] = None

            if self.shared.finish_dump.value:
                break


class WatcherP1(RobotProcess):
    TEST_MESSAGE = "Message from process 1."

    def run(self) -> None:
        time.sleep(1)
        self.heartbeat(self.TEST_MESSAGE)


class WatcherP2(RobotProcess):
    TEST_MESSAGE = "Message from process 2."

    def run(self) -> None:
        time.sleep(1)
        self.heartbeat(self.TEST_MESSAGE)
