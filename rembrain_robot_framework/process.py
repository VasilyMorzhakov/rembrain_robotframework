import logging
import typing as T
from collections import namedtuple
from multiprocessing import Queue


class RobotProcess:
    # Workaround for multiprocessing so we add logging only one time per process
    _is_logger_initialized = False

    def __init__(
            self,
            name: str,
            shared_objects: dict,
            consume_queues: T.Dict[str, Queue],
            publish_queues: T.Dict[str, T.List[Queue]],
            *args,
            **kwargs
    ):
        self.name: str = name
        self.consume_queues: T.Dict[str, Queue] = consume_queues  # queues for reading
        self.publish_queues: T.Dict[str, T.List[Queue]] = publish_queues  # queues for writing
        self.shared: T.Any = namedtuple('_', shared_objects.keys())(**shared_objects)

        self.debug: bool = False
        self.queues_to_clear: T.List[str] = []  # in case of exception this queues are cleared

        self.log = logging.getLogger(f"{self.__class__.__name__} ({self.name})")

    def run(self) -> None:
        raise NotImplementedError()

    def free_resources(self) -> None:
        """
        It frees all occupied resources.
        """
        self.close_objects()
        self.clear_queues()

    def close_objects(self) -> None:
        """It can be overridden in process implementation."""
        pass

    def clear_queues(self) -> None:
        if len(self.queues_to_clear) > 0:
            self.log.info(f"Clearing of queues: {self.queues_to_clear}.")

            for queue in self.queues_to_clear:
                self.clear_queue(queue)

    def clear_queue(self, queue: str) -> None:
        if queue in self.consume_queues:
            while not self.consume_queues[queue].empty():
                self.consume_queues[queue].get(timeout=2.0)

        elif queue in self.publish_queues:
            for q in self.publish_queues[queue]:
                while not q.empty():
                    q.get(timeout=2.0)

    def publish(self, message: T.Any, queue_name: T.Optional[str] = None, clear_on_overflow: bool = False) -> None:
        if len(self.publish_queues.keys()) == 0:
            self.log.error(f"Process \"{self.name}\" has no queues to write to.")
            return

        if queue_name is None:
            if len(self.publish_queues.keys()) != 1:
                self.log.error(f"Process \"{self.name}\" has more than one write queue. Specify a write queue name.")
                return

            queue_name = list(self.publish_queues.keys())[0]

        for q in self.publish_queues[queue_name]:
            if clear_on_overflow:
                while q.full():
                    q.get()

            q.put(message)

    def consume(self, queue_name: T.Optional[str] = None, clear_all_messages: bool = False) -> T.Any:
        if len(self.consume_queues.keys()) == 0:
            self.log.error(f"Process \"{self.name}\" has no queues to read from.")
            return

        if queue_name is None:
            if len(self.consume_queues.keys()) != 1:
                self.log.error(f"Process \"{self.name}\" has more than one read queue. Specify a read queue name.")
                return

            queue_name = list(self.consume_queues.keys())[0]

        message: str = self.consume_queues[queue_name].get()
        if clear_all_messages:
            while not self.consume_queues[queue_name].empty():
                message = self.consume_queues[queue_name].get()

        return message

    def is_full(
            self,
            *,
            publish_queue_name: T.Optional[str] = None,
            consume_queue_name: T.Optional[str] = None
    ) -> bool:
        if publish_queue_name is None and consume_queue_name is None:
            raise Exception("None of params was got!")

        if publish_queue_name and consume_queue_name:
            raise Exception("Only one of params must set!")

        if consume_queue_name:
            return self.consume_queues[consume_queue_name].full()

        for q in self.publish_queues[publish_queue_name]:
            if q.full():
                return True

        return False
