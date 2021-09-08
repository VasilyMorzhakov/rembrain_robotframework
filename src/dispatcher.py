import logging
import platform
import time
import typing as T
from multiprocessing import Process, Queue, Manager

from robot_framework.src import utils
from robot_framework.src.utils import set_logger


class RobotDispatcher:
    """ It passes a config object and a list of created processes."""

    def __init__(
            self,
            config: T.Any = None,
            processes: T.Optional[dict] = None,
            project_description: T.Optional[dict] = None,
            in_cluster: bool = True,
    ):
        self.shared_objects = {}
        self.process_pool = {}
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
                "shared_objects": {},
            }

        set_logger(self.project_description, in_cluster=self.in_cluster)
        logging.info("RobotHost is configuring processes.")

        # compare processes and config
        if len(self.processes) != len(self.config["processes"]):
            raise Exception("Number of processes in config is not the same as passed in __init__.")

        # p[0] is process class, p[1] is the process name
        if any([p not in self.config["processes"] for p in self.processes]):
            raise Exception("Process was not found in config.")

        # create queues
        consume_queues = {}  # consume from queues
        publish_queues = {}  # publish to queues
        for p_name, p_desc in self.config["processes"].items():
            if not p_desc:
                continue

            if "consume" in p_desc:
                if type(p_desc["consume"]) is not list:
                    p_desc["consume"] = [p_desc["consume"]]

                for queue in p_desc["consume"]:
                    if queue in consume_queues:
                        consume_queues[queue].append(p_name)
                    else:
                        consume_queues[queue] = [p_name]

            if "publish" in p_desc:
                if not isinstance(p_desc["publish"], list):
                    p_desc["publish"] = [p_desc["publish"]]

                for queue in p_desc["publish"]:
                    if queue in publish_queues:
                        publish_queues[queue].append(p_name)
                    else:
                        publish_queues[queue] = [p_name]

            # copy other arguments from yaml to a file
            for key in p_desc:
                if key not in ("publish", "consume"):
                    self.processes[p_name][key] = p_desc[key]

        for queue_name, bind_processes in consume_queues.items():
            for process in bind_processes:
                queue = Queue(maxsize=1000)
                self.processes[process]["consume_queues"][queue_name] = queue

                if queue_name not in publish_queues:
                    raise Exception(f"A process {processes} consumes from a queue {queue_name}, but no publish to it.")

                for process_ in publish_queues[queue_name]:
                    if queue_name in self.processes[process_]["publish_queues"]:
                        self.processes[process_]["publish_queues"][queue_name].append(queue)
                    else:
                        self.processes[process_]["publish_queues"][queue_name] = [queue]

        # shared objects
        self.shared_objects = {
            so_name: utils.generate(so, self.manager) for so_name, so in self.config["shared_objects"].items()
        }

    def start_processes(self) -> None:
        for p_name in self.processes.keys():
            self._run_process(p_name)

    def add_process(
            self,
            p_name: str,
            process_class: T.Any,
            publish_queues: T.Optional[T.Dict[str, T.List[Queue]]] = None,
            consume_queues: T.Optional[T.Dict[str, Queue]] = None,
            **kwargs,
    ) -> None:
        if p_name in self.process_pool:
            logging.error(f"Error at creating new process, process {p_name} is already running.")
            raise Exception("Process already exists in pool.")

        if p_name in self.processes:
            logging.error(f"Error at creating new process, process {p_name} already exists in processes.")
            raise Exception("Process already exists in processes.")

        self.processes[p_name] = {
            'process_class': process_class,
            'consume_queues': consume_queues if consume_queues else {},
            'publish_queues': publish_queues if publish_queues else {}
        }

        self._run_process(p_name, **kwargs)
        logging.info(f"New process {p_name} was  created successfully.")

    def add_shared_object(self, so_name: str, so_type: str) -> None:
        if so_name in self.shared_objects.keys():
            raise Exception(f"Shared object {so_name} already exists.")

        self.shared_objects[so_name] = utils.generate(so_type, self.manager)

    def del_shared_object(self, so_name: str) -> None:
        if so_name not in self.shared_objects.keys():
            logging.warning(f"Shared object {so_name} does not exist.")
            return

        del self.shared_objects[so_name]

    def stop_process(self, process_name: str) -> None:
        if process_name not in self.process_pool.keys():
            logging.error(f"Process {process_name} is not running.")
            return

        process: Process = self.process_pool[process_name]
        if process.is_alive():
            process.terminate()
            process.join()

        del self.process_pool[process_name]
        del self.processes[process_name]

    def check_queues_overflow(self, max_queue_size: int = 1000) -> bool:
        if platform.system() == "Darwin":
            return False

        for p_name, process in self.processes.items():
            for q_name, queue in process["consume_queues"].items():
                q_size: int = queue.qsize()

                if q_size > max_queue_size:
                    logging.error(f"Queue {q_name} of process {p_name} has reached {q_size} messages.")
                    time.sleep(5)
                    return True

            for q_name, queues in process["publish_queues"].items():
                for q in queues:
                    q_size: int = q.qsize()

                    if q_size > max_queue_size:
                        logging.error(f"Queue {q_name} of process {p_name} has reached {q_size} messages.")
                        time.sleep(5)
                        return True

        return False

    def run(self, shared_stop_run: T.Any = None, max_queue_size: int = 1000) -> None:
        if platform.system() == "Darwin":
            logging.warning("Checking of queue sizes on this system is not supported.")

        while True:
            if shared_stop_run is not None and shared_stop_run.value:
                break

            if self.check_queues_overflow(max_queue_size):
                break

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
                **self.processes[proc_name],
                **kwargs,
            },
        )
        process.start()
        self.process_pool[proc_name] = process
