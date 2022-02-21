import json
import subprocess
import time

from rembrain_robot_framework import RobotProcess
from rembrain_robot_framework.utils import get_arg_with_env_fallback


class PingProcess(RobotProcess):
    """
    For use in Docker containers

    Out:
        Info about the process to the queue (pushed every second)
        and associated fields (robot and template type)
        in JSON, encoded as a utf-8 binary string

    Args:
        associated_robot: Robot that is used. If not specified, `ROBOT_NAME` env var is used

        template_type: If not specified, `TEMPLATE_TYPE` env var is used
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.associated_robot = get_arg_with_env_fallback(
            kwargs, "associated_robot", "ROBOT_NAME"
        )
        self.template_type = get_arg_with_env_fallback(
            kwargs, "template_type", "TEMPLATE_TYPE"
        )

        # get container ID - it's assumed, that we're in a docker container
        try:
            docker_s = subprocess.check_output(["cat", "/proc/1/cpuset"]).decode(
                "utf-8"
            )
            self.container_id = docker_s[8 : 8 + 12]
        except Exception as e:
            self.container_id = "ERROR"
            self.log.error(e, exc_info=True)

    def run(self):
        self.log.info(f"{self.__class__.__name__} started, name: {self.name}.")

        while True:
            processor_info = {
                "associated_robot": self.associated_robot,
                "template_type": self.template_type,
                "active": self.shared.processor_active.value,
                "id": self.container_id,
            }
            to_send = json.dumps(processor_info).encode("utf-8")
            self.publish(to_send)
            time.sleep(1)
