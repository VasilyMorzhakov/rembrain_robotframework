import os
from envyaml import EnvYAML

from rembrain_robot_framework import RobotDispatcher
from rembrain_robot_framework.examples.common.processes.gui import GUIProcess
from rembrain_robot_framework.examples.common.processes.image_capture import ImageCapture
from rembrain_robot_framework.examples.common.processes.yolo_image_processor import YoloImageProcessor


def run_dispatcher():
    process_map = {
        "gui": GUIProcess,
        "image_capture": ImageCapture,
        "processor": YoloImageProcessor,
    }

    config = EnvYAML(os.path.join(os.path.dirname(__file__), "config", "processes_config.yaml"))
    processes = {p: {"process_class": process_map[p]} for p in config["processes"]}
    project_description = {
        "project": "brainless_robot",
        "subsystem": "local_test_robot",
        "robot": "local_example_robot"
    }

    robot_dispatcher = RobotDispatcher(
        config, processes, project_description=project_description, in_cluster=False
    )
    robot_dispatcher.start_processes()
    robot_dispatcher.run(robot_dispatcher.shared_objects["exit_flag"])
    robot_dispatcher.log_listener.stop()


if __name__ == "__main__":
    run_dispatcher()
