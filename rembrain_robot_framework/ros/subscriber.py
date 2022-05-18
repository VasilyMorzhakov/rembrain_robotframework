import os


import rclpy
import websocket
from envyaml import EnvYAML
from rclpy.node import Node
from rembrain_robot_framework.ros.exceptions import RosException
from rembrain_robot_framework.ws.command_type import WsCommandType
from rembrain_robot_framework.ws.request import WsRequest
from std_msgs.msg import String


class WsSubscriber(Node):

    def __init__(self, config_file):
        super().__init__(self.__class__.__name__)

        config = EnvYAML(config_file)
        self.exchange = config["exchange"]
        queue = config["queue"]
        queue_size = config["queue_size"]
        self.item_type = config["item_type"]

        self.ws = websocket.WebSocket()
        self.ws_url = os.environ["WEBSOCKET_GATE_URL"]
        self.robot_name = os.environ["ROBOT_NAME"]
        self.username = os.environ["RRF_USERNAME"]
        self.password = os.environ["RRF_PASSWORD"]

        # todo there are a lot of other types
        if self.item_type == 'String':
            self.subscription = self.create_subscription(
                String, queue, self.listener_callback, queue_size
            )
        else:
            raise RosException("Unknow item type !")

    def listener_callback(self, msg):
        if not self.ws.connected:
            self.ws = websocket.WebSocket()
            self.ws.connect(self.ws_url)

        self.ws.send(
            WsRequest(
                command=WsCommandType.PUSH,
                exchange=self.exchange,
                robot_name=self.robot_name,
                username=self.username,
                password=self.password,
                message=msg
            ).json()
        )

        # todo how to check response
        self.ws.recv()


def main(args=None):
    rclpy.init(args=args)

    ws_subscriber = WsSubscriber()

    rclpy.spin(ws_subscriber)

    ws_subscriber.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
