import glob
import logging
import time
import os
import unittest
from contextlib import redirect_stderr
import re

from rembrain_robot_framework import RobotDispatcher
from rembrain_robot_framework.tests.util import load_config, generate_process_dict
from rembrain_robot_framework.tests.util.processes import FailingProcess

process_map = {
    "failing_process": FailingProcess
}


class TestLogging(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        # Check that an out dir exists
        cls.out_dir_path = os.path.join(os.path.dirname(__file__), "out")
        if not os.path.exists(cls.out_dir_path):
            os.makedirs(cls.out_dir_path)

    @classmethod
    def tearDownClass(cls) -> None:
        files = glob.glob(f"{cls.out_dir_path}/*")
        for f in files:
            os.remove(f)

    def test_crashing_doesnt_create_another_logger(self) -> None:
        """
        Testing that there are no duplicate loggers by creating a count-up-then-fail process
        Keeping it running for a couple failures
        Test passes if there are no count repeats in the end log result
        """
        cfg = load_config(self, self.test_crashing_doesnt_create_another_logger.__name__)
        processes = generate_process_dict(cfg, process_map)
        output_file = os.path.join(self.out_dir_path, f"{self.test_crashing_doesnt_create_another_logger.__name__}_output.txt")

        # Assuming we're redirecting to stderr, if things change - gotta change here
        # for some reason, redirecting to io.StringIO redirects only one line
        # probably some multiprocessing issue.
        # For now working around it by writing out to an output file and then reading it
        with redirect_stderr(open(output_file, "w")):
            dispatcher = RobotDispatcher(cfg, processes, in_cluster=False)
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
