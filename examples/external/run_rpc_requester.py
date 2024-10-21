import os
import sys

from envyaml import EnvYAML

# Adding the repository root to the sys path so exports work properly

sys.path.append(os.path.abspath(os.path.join(__file__, "..", "..", "..")))

from examples.external.processes import Requester
from examples.external.utils import query_env_vars  # noqa: E402
from rembrain_robot_framework import RobotDispatcher
from rembrain_robot_framework.processes import WsRobotProcess



def run_dispatcher():
    process_map = {
        "process_requester":Requester,
        "command_sender":WsRobotProcess
    }

    config = EnvYAML(
        os.path.join(os.path.dirname(__file__), "config", "requester_config.yaml")
    )
    processes = {p: {"process_class": process_map[p]} for p in config["processes"]}

    robot_dispatcher = RobotDispatcher(config, processes, in_cluster=False)
    robot_dispatcher.start_processes()
    robot_dispatcher.run(robot_dispatcher.shared_objects["exit_flag"])
    robot_dispatcher.stop_logging()


if __name__ == "__main__":
    required_vars = ["WEBSOCKET_GATE_URL", "ROBOT_NAME", "RRF_USERNAME", "RRF_PASSWORD"]
    if not query_env_vars(required_vars):
        sys.exit(0)

    run_dispatcher()
