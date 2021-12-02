import os
import sys

from envyaml import EnvYAML

# Adding the repository root to the sys path so exports work properly
sys.path.append(os.path.abspath(os.path.join(__file__, "..", "..", "..")))

from examples.common.processes import GUIProcess, ImageCapture, YoloImageProcessor  # noqa: E402
from rembrain_robot_framework import RobotDispatcher  # noqa: E402


def run_dispatcher():
    process_map = {
        "gui": GUIProcess,
        "image_capture": ImageCapture,
        "processor": YoloImageProcessor,
    }

    config = EnvYAML(os.path.join(os.path.dirname(__file__), "config", "processes_config.yaml"))
    processes = {p: {"process_class": process_map[p]} for p in config["processes"]}

    robot_dispatcher = RobotDispatcher(config, processes, in_cluster=False)
    robot_dispatcher.start_processes()
    robot_dispatcher.run(robot_dispatcher.shared_objects["exit_flag"])
    robot_dispatcher.stop_logging()


if __name__ == "__main__":
    run_dispatcher()
