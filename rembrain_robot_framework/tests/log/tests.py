import json
import os
import re
import time
import unittest
from contextlib import redirect_stderr
from io import StringIO
from multiprocessing import Process, Value
from unittest import mock

import websocket
import yaml

from rembrain_robot_framework import RobotDispatcher
from rembrain_robot_framework.tests.log.processes.failing_process import FailingProcess
from rembrain_robot_framework.tests.log.websocket_server import WebsocketServer


class TestLogging(unittest.TestCase):
    def test_crashing_doesnt_create_another_logger(self) -> None:
        """
        Testing that there are no duplicate loggers by creating a count-up-then-fail process
        Keeping it running for a couple failures
        Test passes if there are no count repeats in the end log result
        """
        config: dict = self._read_config_file("config1.yaml")
        process_map = {"failing_process": FailingProcess}
        processes = {p: {"process_class": process_map[p]} for p in config["processes"]}

        std_errors = StringIO()
        with redirect_stderr(std_errors):
            dispatcher = RobotDispatcher(config, processes, in_cluster=False)
            dispatcher.start_processes()
            # Wait for more than 10 or so seconds because process restart takes 5 seconds
            time.sleep(15)

        dispatcher.stop_process("failing_process")

        std_errors.seek(0)
        log_data = std_errors.read()
        logged_counts = ""
        count_regex = r"Count: (\d)"

        for line in log_data.splitlines():
            m = re.search(count_regex, line)
            if m is not None:
                logged_counts += f"{m.group(1)}, "

        self.assertNotIn("0, 0", logged_counts)
        self.assertIn("0, 1, 2, 3", logged_counts)

    def test_logging_to_websocket_works(self):
        """
        Check that logging to websocket/remote server works for RobotProcess and RobotDispatcher
        Set up an "echo" websocket server that keeps all received messages
        Then mock out WEBSOCKET_GATE_URL so all logs get sent to this ws server
        Run the dispatcher and then get logged messages in the end
        """

        ws_port = "15735"
        test_message = "It's test message!"
        config: dict = self._read_config_file("config2.yaml")

        process_map = {"failing_process": FailingProcess}
        processes = {p: {"process_class": process_map[p]} for p in config["processes"]}
        close_flag = Value('b', False)

        ws_server = WebsocketServer(ws_port, test_message)
        p = Process(target=ws_server.start, args=(close_flag,))
        p.start()
        time.sleep(2.0)

        env_overrides = {
            "WEBSOCKET_GATE_URL": f"ws://127.0.0.1:{ws_port}",
            "ROBOT_NAME": "framework_test",
            "ROBOT_PASSWORD": "framework_test",
        }

        with mock.patch.dict("os.environ", env_overrides):
            # Run the Dispatcher
            dispatcher = RobotDispatcher(config, processes, in_cluster=False)
            dispatcher.start_processes()
            time.sleep(5)

            # Get logged messages back from the websocket
            ws = websocket.WebSocket()
            ws.connect(os.environ["WEBSOCKET_GATE_URL"])
            ws.send(test_message)
            logs = json.loads(ws.recv())

            # Close the websocket
            print("Closing")
            close_flag.value = True
            p.join()

        # Check that Count messages are in the log output
        messages = list(map(lambda m: m["message"]["message"], logs))

        self.assertIn("RobotHost is configuring processes.", messages)
        self.assertIn("Count: 0", messages)

    @classmethod
    def _read_config_file(cls, cfg_file: str) -> dict:
        cfg_path: str = os.path.join(os.path.dirname(__file__), cfg_file)
        with open(cfg_path) as f:
            return yaml.load(f, Loader=yaml.BaseLoader)


if __name__ == "__main__":
    unittest.main()
