import os
import sys

from envyaml import EnvYAML

# Adding the repository root to the sys path so exports work properly
sys.path.append(os.path.abspath(os.path.join(__file__, "..", "..", "..")))

from examples.common.processes import YoloImageProcessor, ImageCapture  # noqa: E402
from examples.external.config_gui import query_env_vars  # noqa: E402
from rembrain_robot_framework import RobotDispatcher  # noqa: E402
from rembrain_robot_framework.processes import WsRobotProcess, VideoUnpacker, VideoPacker  # noqa: E402


def run_dispatcher():
    process_map = {
        "image_capture": ImageCapture,
        "processor": YoloImageProcessor,
        "video_packer": VideoPacker,
        "video_unpacker": VideoUnpacker,
        "orig_receiver": WsRobotProcess,
        "processed_pusher": WsRobotProcess,
    }

    config = EnvYAML(os.path.join(os.path.dirname(__file__), "config", "processor_config.yaml"))
    processes = {p: {"process_class": process_map[p]} for p in config["processes"]}
    project_description = {
        "project": "rembrain_robotframework_examples",
        "subsystem": "remote_example_processor",
        "robot": os.environ["ROBOT_NAME"]
    }

    robot_dispatcher = RobotDispatcher(
        config, processes, project_description=project_description, in_cluster=False
    )
    robot_dispatcher.start_processes()
    robot_dispatcher.run()
    robot_dispatcher.log_listener.stop()


if __name__ == "__main__":
    # todo remove it! - it is hardcode
    if not os.environ.get("WEBSOCKET_GATE_URL"):
        os.environ["WEBSOCKET_GATE_URL"] = "wss://monitor-dev.rembrain.ai:5443"

    required_vars = ["WEBSOCKET_GATE_URL", "ROBOT_NAME", "ROBOT_PASSWORD"]
    if not query_env_vars(required_vars):
        sys.exit(0)

    run_dispatcher()
