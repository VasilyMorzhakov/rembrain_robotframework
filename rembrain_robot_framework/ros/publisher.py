import os

import rclpy
import websocket
from envyaml import EnvYAML
from rclpy.node import Node
from rembrain_robot_framework.ros.exceptions import RosException
from rembrain_robot_framework.ws.command_type import WsCommandType
from rembrain_robot_framework.ws.request import WsRequest
from std_msgs.msg import String


class WsPublisher(Node):
    def __init__(self, config_file):
        super().__init__(self.__class__.__name__)

        config = EnvYAML(config_file)
        queue = config["queue"]
        queue_size = config["queue_size"]
        self.exchange = config["exchange"]
        self.item_type = config["item_type"]

        self.ws = websocket.WebSocket()
        self.ws_url = os.environ["WEBSOCKET_GATE_URL"]
        self.robot_name = os.environ["ROBOT_NAME"]
        self.username = os.environ["RRF_USERNAME"]
        self.password = os.environ["RRF_PASSWORD"]

        # todo there are a lot of other types
        if self.item_type == 'String':
            self.publisher_ = self.create_publisher(String, queue, queue_size)
        else:
            raise RosException("Unknow item type !")

        self.handler = self.create_timer(0.5, self.get_from_ws_callback)

    def get_from_ws_callback(self):
        if not self.ws.connected:
            self.ws = websocket.WebSocket()
            self.ws.connect(self.ws_url)

        self.ws.send(
            WsRequest(
                command=WsCommandType.PULL,
                exchange=self.exchange,
                robot_name=self.robot_name,
                username=self.username,
                password=self.password,
            ).json()
        )

        # todo how to check response
        response = self.ws.recv()

        if self.item_type == 'String':
            msg = String()
        else:
            raise RosException("Unknow item type !")

        msg.data = response
        self.publisher_.publish(msg)
        self.get_logger().info(f'Publishing completed.')


if __name__ == '__main__':
    args = None

    ws_publisher = WsPublisher(config_file="config_example.yaml")
    rclpy.spin(ws_publisher)

    ws_publisher.destroy_node()
    rclpy.shutdown()
