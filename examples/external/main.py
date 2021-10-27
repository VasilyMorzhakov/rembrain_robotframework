import os

from envyaml import EnvYAML

from rembrain_robot_framework import RobotDispatcher

if __name__ == "__main__":
    process_map = {
        # todo add processes
    }

    config = EnvYAML(os.path.join(os.path.dirname(__file__), "config", "processes_config.yaml"))
    processes = {p: {"process_class": process_map[p]} for p in config["processes"]}
    project_description = {
        "project": "brainless_robot",
        "subsystem": "external_test_robot",
        "robot": os.environ["ROBOT_NAME"]
    }

    robot_dispatcher = RobotDispatcher(
        config, processes, project_description=project_description, in_cluster=False
    )
    robot_dispatcher.start_processes()
    robot_dispatcher.run()
