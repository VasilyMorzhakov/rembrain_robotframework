import os

# Adding the repository root to the sys path so exports work properly
import sys
sys.path.append(os.path.abspath(os.path.join(__file__, "..", "..", "..")))

from envyaml import EnvYAML

from examples.common.processes import ImageCapture, GUIProcess, DepthMixin
from examples.external.config_gui import query_env_vars
from rembrain_robot_framework import RobotDispatcher
from rembrain_robot_framework.processes import WsRobotProcess, VideoPacker, VideoUnpacker


def run_dispatcher():
    process_map = {
        "gui": GUIProcess,
        "image_capture": ImageCapture,
        "depth_mixin": DepthMixin,
        "video_packer": VideoPacker,
        "orig_pusher": WsRobotProcess,
        "processed_receiver": WsRobotProcess,
        "video_unpacker": VideoUnpacker
    }

    config = EnvYAML(os.path.join(os.path.dirname(__file__), "config", "robot_config.yaml"))
    processes = {p: {"process_class": process_map[p]} for p in config["processes"]}
    project_description = {
        "project": "rembrain_robotframework_examples",
        "subsystem": "remote_example_robot",
        "robot": os.environ["ROBOT_NAME"]
    }

    robot_dispatcher = RobotDispatcher(
        config, processes, project_description=project_description, in_cluster=False
    )
    robot_dispatcher.start_processes()
    robot_dispatcher.run(robot_dispatcher.shared_objects["exit_flag"])
    robot_dispatcher.log_listener.stop()


if __name__ == "__main__":
    if not os.environ.get("WEBSOCKET_GATE_URL"):
        os.environ["WEBSOCKET_GATE_URL"] = "wss://monitor-dev.rembrain.ai:5443"
    required_vars = ["WEBSOCKET_GATE_URL", "ROBOT_NAME", "ROBOT_PASSWORD"]
    if not query_env_vars(required_vars):
        sys.exit(0)
    run_dispatcher()