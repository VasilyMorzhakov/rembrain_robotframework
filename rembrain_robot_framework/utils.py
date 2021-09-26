from __future__ import annotations

import logging
import time
import typing as T
from ctypes import c_bool, c_int, c_float, c_char_p
from functools import wraps
from multiprocessing import Value, Lock, Manager

from rembrain_robot_framework.logger import set_logger


def generate(name: str, manager: Manager) -> T.Any:
    if name == 'dict':
        return manager.dict()

    if name == 'list':
        return manager.list()

    if name == 'Lock':
        return Lock()

    if name == 'Value:bool':
        return Value(c_bool, False)

    if name == 'Value:int':
        return Value(c_int, 0)

    if name == 'Value:float':
        return Value(c_float, 0.0)

    if name == 'Value:string':
        return Value(c_char_p, '')

    raise Exception('Wrong type to generate')


def keep_alive(start_process_func: T.Callable) -> T.Callable:
    @wraps(start_process_func)
    def alive_cycle(process_class, *args, **kwargs) -> None:
        name: str = kwargs["name"] if "name" in kwargs else "unknown"

        while True:
            try:
                start_process_func(process_class, *args, **kwargs)
            except Exception as e:
                logging.warning(f"Exception happend in process {name}")
                logging.error(e, exc_info=True)
                time.sleep(1.0)

            if "keep_alive" in kwargs and not kwargs["keep_alive"]:
                logging.info(f"process {name} is closing")
                break

            logging.info(f"Restarting process {name}")
            time.sleep(5.0)

    return alive_cycle


@keep_alive
def start_process(process_class: T.Any, *args, **kwargs) -> None:
    process: T.Any = None
    set_logger(kwargs["project_description"], kwargs.get("in_cluster", True))

    try:
        process = process_class(*args, **kwargs)
        process.run()
    finally:
        if process:
            process.free_resources()
