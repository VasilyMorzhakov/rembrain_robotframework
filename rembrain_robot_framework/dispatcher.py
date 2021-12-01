import logging
import platform
import time
import typing as T
from logging.handlers import QueueHandler, QueueListener
from multiprocessing import Process, Queue, Manager

from rembrain_robot_framework import utils
from rembrain_robot_framework.logger.utils import setup_logging


class RobotDispatcher:
    DEFAULT_QUEUE_SIZE = 50

    def __init__(
            self,
            config: T.Any = None,
            processes: T.Optional[dict] = None,
            project_description: T.Optional[dict] = None,
            in_cluster: bool = True,
    ):
        self.shared_objects = {}
        self.process_pool: T.Dict[str, Process] = {}
        self.in_cluster: bool = in_cluster
        self.project_description = {} if project_description is None else project_description

        self.manager = Manager()
        self.processes = {} if processes is None else processes
        for name, p in self.processes.items():
            if "consume_queues" not in p:
                p["consume_queues"] = {}

            if "publish_queues" not in p:
                p["publish_queues"] = {}

        self.config = config
        if self.config is None:
            self.config = {
                "processes": {},
                "queues_sizes": {},
                "shared_objects": {},
            }

        self.log_queue: T.Optional[Queue] = None
        self.log_listener: T.Optional[QueueListener] = None
        self.log: T.Optional[logging.Logger] = None
        self.set_logging(project_description, in_cluster)

        self.log.info("RobotHost is configuring processes.")

        # compare processes and config
        if len(self.processes) != len(self.config["processes"]):
            raise Exception("Number of processes in config is not the same as passed in __init__.")

        # p[0] is process class, p[1] is the process name
        if any([p not in self.config["processes"] for p in self.processes]):
            raise Exception("Process was not found in config.")

        # create queues
        consume_queues = {}  # consume from queues
        publish_queues = {}  # publish to queues
        for process_name, process_params in self.config["processes"].items():
            if not process_params:
                continue

            if "consume" in process_params:
                if type(process_params["consume"]) is not list:
                    process_params["consume"] = [process_params["consume"]]

                for queue in process_params["consume"]:
                    if queue in consume_queues:
                        consume_queues[queue].append(process_name)
                    else:
                        consume_queues[queue] = [process_name]

            if "publish" in process_params:
                if not isinstance(process_params["publish"], list):
                    process_params["publish"] = [process_params["publish"]]

                for queue in process_params["publish"]:
                    if queue in publish_queues:
                        publish_queues[queue].append(process_name)
                    else:
                        publish_queues[queue] = [process_name]

            # copy other arguments from yaml to a file
            for key in process_params:
                if key not in ("publish", "consume"):
                    self.processes[process_name][key] = process_params[key]

        for queue_name, bind_processes in consume_queues.items():
            for process in bind_processes:
                queue_size = int(
                    self.config.get("queues_sizes", {}).get(queue_name, self.DEFAULT_QUEUE_SIZE)
                )

                queue = self.manager.Queue(maxsize=queue_size)
                self.processes[process]["consume_queues"][queue_name] = queue

                if queue_name not in publish_queues:
                    raise Exception(f"A process {processes} consumes from a queue {queue_name}, but no publish to it.")

                for process_ in publish_queues[queue_name]:
                    if queue_name in self.processes[process_]["publish_queues"]:
                        self.processes[process_]["publish_queues"][queue_name].append(queue)
                    else:
                        self.processes[process_]["publish_queues"][queue_name] = [queue]

        # shared objects
        if 'shared_objects' in self.config.keys():
            self.shared_objects = {
                name: utils.generate(obj, self.manager) for name, obj in self.config["shared_objects"].items()
            }

    def set_logging(self, project_description: dict, in_cluster: bool) -> None:
        # Set up logging
        self.log_queue, self.log_listener = setup_logging(project_description, in_cluster)
        self.log_listener.start()

        self.log = logging.getLogger("RobotDispatcher")

        # Clear any handlers that have already existed
        self.log.handlers.clear()
        self.log.setLevel(logging.INFO)
        self.log.addHandler(QueueHandler(self.log_queue))

        # Don't propagate to root logger
        self.log.propagate = False

    def start_processes(self) -> None:
        for process_name in self.processes.keys():
            self._run_process(process_name)
            proc = self.process_pool[process_name]
            self.log.info(f"Process {process_name} on PID {proc.pid} started")

    def add_process(
            self,
            process_name: str,
            process_class: T.Any,
            publish_queues: T.Optional[T.Dict[str, T.List[Queue]]] = None,
            consume_queues: T.Optional[T.Dict[str, Queue]] = None,
            **kwargs,
    ) -> None:
        if process_name in self.process_pool:
            self.log.error(f"Error at creating new process, process {process_name} is already running.")
            raise Exception("Process already exists in pool.")

        if process_name in self.processes:
            self.log.error(f"Error at creating new process, process {process_name} already exists in processes.")
            raise Exception("Process already exists in processes.")

        self.processes[process_name] = {
            'process_class': process_class,
            'consume_queues': consume_queues if consume_queues else {},
            'publish_queues': publish_queues if publish_queues else {}
        }

        self._run_process(process_name, **kwargs)
        self.log.info(f"New process {process_name} was  created successfully.")

    def add_shared_object(self, object_name: str, object_type: str) -> None:
        if object_name in self.shared_objects.keys():
            raise Exception(f"Shared object {object_name} already exists.")

        self.shared_objects[object_name] = utils.generate(object_type, self.manager)

    def del_shared_object(self, object_name: str) -> None:
        if object_name not in self.shared_objects.keys():
            self.log.warning(f"Shared object {object_name} does not exist.")
            return

        del self.shared_objects[object_name]

    def stop_process(self, process_name: str) -> None:
        if process_name not in self.process_pool.keys():
            self.log.error(f"Process {process_name} is not running.")
            return

        process: Process = self.process_pool[process_name]
        if process.is_alive():
            process.terminate()
            process.join()

        del self.process_pool[process_name]
        del self.processes[process_name]

    def check_queues_overflow(self) -> bool:
        is_overflow = False
        if platform.system() == "Darwin":
            return is_overflow

        for p_name, process in self.processes.items():
            for q_name, queue in process["consume_queues"].items():
                q_size: int = queue.qsize()

                if queue._maxsize - q_size <= int(queue._maxsize * 0.1):
                    self.log.warning(f"Consume queue {q_name} of process {p_name} has reached {q_size} messages.")
                    is_overflow = True

            for q_name, queues in process["publish_queues"].items():
                for q in queues:
                    q_size: int = q.qsize()

                    if q._maxsize - q_size <= int(q._maxsize * 0.1):
                        self.log.warning(f"Publish queue {q_name} of process {p_name} has reached {q_size} messages.")
                        is_overflow = True

        if is_overflow:
            time.sleep(5)

        return is_overflow

    def run(self, shared_stop_run: T.Any = None) -> None:
        if platform.system() == "Darwin":
            self.log.warning("Checking of queue sizes on this system is not supported.")

        while True:
            if shared_stop_run is not None and shared_stop_run.value:
                break

            self.check_queues_overflow()
            time.sleep(2)

    def _run_process(self, proc_name: str, **kwargs) -> None:
        process = Process(
            target=utils.start_process,
            daemon=True,
            kwargs={
                "name": proc_name,
                "in_cluster": self.in_cluster,
                "shared_objects": self.shared_objects,
                "project_description": self.project_description,
                "logging_queue": self.log_queue,
                **self.processes[proc_name],
                **kwargs,
            }
        )
        process.start()
        self.process_pool[proc_name] = process
