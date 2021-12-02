import json
import os
import re
import time
from contextlib import redirect_stderr
from io import StringIO
from multiprocessing import Process, Value
from unittest import mock

import websocket
from envyaml import EnvYAML

from rembrain_robot_framework import RobotDispatcher
from rembrain_robot_framework.tests.log.processes import FailingProcess
from rembrain_robot_framework.tests.log.websocket_server import WebsocketServer


def test_crashing_doesnt_create_another_logger() -> None:
    """
    Testing that there are no duplicate loggers by creating a count-up-then-fail process
    Keeping it running for a couple failures
    Test passes if there are no count repeats in the end log result
    """
    config = EnvYAML(os.path.join(os.path.dirname(__file__), "configs", "config1.yaml"))
    process_map = {"failing_process": FailingProcess}
    processes = {p: {"process_class": process_map[p]} for p in config["processes"]}

    std_errors = StringIO()
    with redirect_stderr(std_errors):
        robot_dispatcher = RobotDispatcher(config, processes, in_cluster=False)
        robot_dispatcher.start_processes()
        # Wait for more than 10 or so seconds because process restart takes 5 seconds
        time.sleep(15)

    robot_dispatcher.stop_process("failing_process")
    robot_dispatcher.stop_logging()

    std_errors.seek(0)
    log_data = std_errors.read()
    logged_counts = ""
    count_regex = r"Count: (\d)"

    for line in log_data.splitlines():
        m = re.search(count_regex, line)
        if m is not None:
            logged_counts += f"{m.group(1)}, "

    assert "0, 0" not in logged_counts
    assert "0, 1, 2, 3" in logged_counts


def test_logging_to_websocket_works() -> None:
    """
    Check that logging to websocket/remote server works for RobotProcess and RobotDispatcher
    Set up an "echo" websocket server that keeps all received messages
    Then mock out WEBSOCKET_GATE_URL so all logs get sent to this ws server
    Run the dispatcher and then get logged messages in the end
    """

    ws_port = "15735"
    test_message = "It's test message!"
    close_flag = Value('b', False)

    config = EnvYAML(os.path.join(os.path.dirname(__file__), "configs", "config2.yaml"))
    process_map = {"failing_process": FailingProcess}
    processes = {p: {"process_class": process_map[p]} for p in config["processes"]}

    ws_server = WebsocketServer(ws_port, test_message)
    p = Process(target=ws_server.start, args=(close_flag,))
    p.start()
    time.sleep(2.0)

    env_overrides = {
        "WEBSOCKET_GATE_URL": f"ws://127.0.0.1:{ws_port}",
        "ROBOT_NAME": "framework_test",
        "RRF_USERNAME": "framework_test",
        "RRF_PASSWORD": "framework_test",
    }

    with mock.patch.dict("os.environ", env_overrides):
        # Run the Dispatcher
        robot_dispatcher = RobotDispatcher(config, processes, in_cluster=False)
        robot_dispatcher.start_processes()
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
        robot_dispatcher.stop_logging()

    # Check that Count messages are in the log output
    messages = list(map(lambda m: m["message"]["message"], logs))
    assert "RobotHost is configuring processes." in messages
    assert "Count: 0" in messages
