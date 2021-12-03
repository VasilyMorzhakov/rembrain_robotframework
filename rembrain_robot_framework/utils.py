import logging
import time
import typing as T
from ctypes import c_bool, c_int, c_float, c_char_p
from functools import wraps
from logging.handlers import QueueHandler
from multiprocessing import Value, Lock, Manager


def generate(name: str, manager: Manager) -> T.Any:
    # Important: Since we are using a separate context for the RobotProcesses, always instantiate from manager
    if name == 'dict':
        return manager.dict()

    if name == 'list':
        return manager.list()

    if name == 'Lock':
        return manager.Lock()

    if name == 'Value:bool':
        return manager.Value(c_bool, False)

    if name == 'Value:int':
        return manager.Value(c_int, 0)

    if name == 'Value:float':
        return manager.Value(c_float, 0.0)

    if name == 'Value:string':
        return manager.Value(c_char_p, '')

    raise Exception('Wrong type to generate')


def keep_alive(start_process_func: T.Callable) -> T.Callable:
    @wraps(start_process_func)
    def alive_cycle(process_class, *args, **kwargs) -> None:
        name: str = kwargs["name"] if "name" in kwargs else "unknown"

        # Initialize logging for this process
        # Create a handler to the log_queue on the root handler
        # So any logger that is created inside the process will use this handler
        log_queue = kwargs["logging_queue"]
        log_level = kwargs.get("log_level", "INFO").upper()

        root_logger = logging.getLogger()
        root_logger.setLevel(log_level)
        root_logger.handlers.clear()
        root_logger.handlers.append(QueueHandler(log_queue))

        dispatcher_log = logging.getLogger("RobotDispatcher")

        while True:
            try:
                start_process_func(process_class, *args, **kwargs)
            except Exception as e:
                dispatcher_log.warning(f"Exception happened in process {name}")
                dispatcher_log.error(e, exc_info=True)
                time.sleep(1.0)

            if "keep_alive" in kwargs and not kwargs["keep_alive"]:
                dispatcher_log.info(f"process {name} is closing")
                break

            dispatcher_log.info(f"Restarting process {name}")
            time.sleep(5.0)

    return alive_cycle


@keep_alive
def start_process(process_class, *args, **kwargs) -> None:
    process = None

    try:
        process = process_class(*args, **kwargs)
        process.run()
    finally:
        if process:
            process.free_resources()
