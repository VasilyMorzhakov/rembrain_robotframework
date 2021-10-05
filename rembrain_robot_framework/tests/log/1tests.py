import os
import re
import shutil
import time
import unittest
from contextlib import redirect_stderr

import yaml

from rembrain_robot_framework import RobotDispatcher
from rembrain_robot_framework.tests.log.processes.failing_process import FailingProcess


class TestLogging(unittest.TestCase):
    OUT_DIR_PATH = os.path.join(os.path.dirname(__file__), "out")

    @classmethod
    def setUpClass(cls) -> None:
        # Check that an out dir exists
        if not os.path.exists(cls.OUT_DIR_PATH):
            os.makedirs(cls.OUT_DIR_PATH)

    @classmethod
    def tearDownClass(cls) -> None:
        shutil.rmtree(cls.OUT_DIR_PATH)

    def test_crashing_doesnt_create_another_logger(self) -> None:
        """
        Testing that there are no duplicate loggers by creating a count-up-then-fail process
        Keeping it running for a couple failures
        Test passes if there are no count repeats in the end log result
        """
        with open(os.path.join(os.path.dirname(__file__), "config.yaml")) as file:
            config: dict = yaml.load(file, Loader=yaml.BaseLoader)

        process_map = {"failing_process": FailingProcess}
        processes = {p: {"process_class": process_map[p]} for p in config["processes"]}
        output_file = os.path.join(self.OUT_DIR_PATH, "output.txt")

        # Assuming we're redirecting to stderr, if things change - gotta change here
        # for some reason, redirecting to io.StringIO redirects only one line
        # probably some multiprocessing issue.
        # For now working around it by writing out to an output file and then reading it
        with redirect_stderr(open(output_file, "w")):
            dispatcher = RobotDispatcher(config, processes, in_cluster=False)
            dispatcher.start_processes()
            time.sleep(15)

        with open(output_file, "r") as f:
            log_data = f.read()
            logged_counts = ""
            count_regex = r"Count: (\d)"

            for line in log_data.splitlines():
                m = re.search(count_regex, line)
                if m is not None:
                    logged_counts += f"{m.group(1)}, "

        self.assertNotIn("0, 0", logged_counts)
        self.assertIn("0, 1, 2, 3", logged_counts)


if __name__ == "__main__":
    unittest.main()
