import logging
import typing as T
from collections import namedtuple
from multiprocessing import Queue
from threading import Thread
from uuid import uuid4

from rembrain_robot_framework.models.named_message import NamedMessage
from rembrain_robot_framework.services.watcher import Watcher
from rembrain_robot_framework.utils import ConfigurationError, ComputationFailure

from rembrain_robot_framework.util.stack_monitor import StackMonitor


class RobotProcess:
    # TODO: add doctrings for this parameters
    def __init__(
            self,
            name: str,
            shared_objects: dict,
            consume_queues: T.Dict[str, Queue],
            publish_queues: T.Dict[str, T.List[Queue]],
            system_queues: T.Dict[str, Queue],
            watcher: Watcher,
            *args,
            **kwargs
    ):
        self.name: str = name

        self._consume_queues: T.Dict[str, Queue] = consume_queues  # queues for reading
        self._publish_queues: T.Dict[str, T.List[Queue]] = publish_queues  # queues for writing

        self._shared: T.Any = namedtuple('_', shared_objects.keys())(**shared_objects)

        self._system_queues: T.Dict[str, Queue] = system_queues
        self._received_named_messages = {}

        self.queues_to_clear: T.List[str] = []  # in case of exception this queues are cleared
        self.log = logging.getLogger(f"{self.__class__.__name__} ({self.name})")

        self._stack_monitor: T.Optional[StackMonitor] = None
        if "monitoring" in kwargs and kwargs['monitoring']:
            self._init_monitoring(self.name)

        self.watcher = watcher

    def run(self) -> None:
        raise NotImplementedError()

    @property
    def consume_queues(self):
        return self._consume_queues

    @property
    def publish_queues(self):
        return self._publish_queues

    @property
    def shared(self):
        # TODO remove shared variables
        return self._shared

    def free_resources(self) -> None:
        """
        It frees all occupied resources.
        """
        if self._stack_monitor:
            self._stack_monitor.stop_monitoring()

        self.close_objects()
        self.clear_queues()

    # todo it's ridiculous - free_resources may be called with super()
    def close_objects(self) -> None:
        """It can be overridden in process implementation."""
        pass

    def clear_queues(self) -> None:
        if len(self.queues_to_clear) > 0:
            self.log.info(f"Clearing of queues: {self.queues_to_clear}.")

            for queue in self.queues_to_clear:
                self.clear_queue(queue)

    def clear_queue(self, queue: str) -> None:
        if queue in self._consume_queues:
            while not self._consume_queues[queue].empty():
                self._consume_queues[queue].get(timeout=2.0)

        elif queue in self._publish_queues:
            for q in self._publish_queues[queue]:
                while not q.empty():
                    q.get(timeout=2.0)

    def publish(self, message: T.Any, queue_name: T.Optional[str] = None, clear_on_overflow: bool = False,
                named: bool = False) -> T.Optional[str]:
        """
        Sends message to all processes that are configured to listen to the queue_name. If there are several processes
        listening than every one will receive a copy of the message.
        :param message: Any pickable data to transfer over interprocess queues.
        :param queue_name: Name of the queue to send message to. If there is only one output queue it's possible to omit
        this argument, it will pick this single queue by default (and raise ConfigurationError if there is number of output
         queues != 1.
        :type queue_name: str
        :param clear_on_overflow: If this parameter is set and a queue to write is full, publish will empty the queue
        before publishing new messages
        :type clear_on_overflow: bool
        :param named: If set, it passes message as NamedMessage, adding current process name and message id for the
        receiving code to be able to respond to this.
        :type named: bool
        :return: If was called with named=True return message id, None otherwise.
        :rtype: T.Optional[str]
        """
        if len(self._publish_queues.keys()) == 0:
            self.log.error(f"Process \"{self.name}\" has no queues to write.")
            raise ConfigurationError(f"Publish called with 0 output queues for process {self.name}")

        if queue_name is None:
            if len(self._publish_queues.keys()) != 1:
                self.log.error(f"Process \"{self.name}\" has more than one write queue. Specify a write queue name.")
                raise ConfigurationError(f"Publish called with >1 output queues for process {self.name}")

            queue_name = list(self._publish_queues.keys())[0]

        message_id: T.Optional[str] = None
        if named:
            message_id = str(uuid4())
            message = NamedMessage(id=message_id, client_process=self.name, data=message)

        for q in self._publish_queues[queue_name]:
            if clear_on_overflow:
                while q.full():
                    q.get()

            q.put(message)

        return message_id

    def consume(self, queue_name: T.Optional[str] = None, clear_all_messages: bool = False) -> T.Any:
        if len(self._consume_queues.keys()) == 0:
            raise ConfigurationError(f"Consume called with 0 input queues for process {self.name}")

        if queue_name is None:
            if len(self._consume_queues.keys()) != 1:
                raise ConfigurationError(f"Consume called with >1 input queues for process {self.name}")

            queue_name = list(self._consume_queues.keys())[0]

        message: str = self._consume_queues[queue_name].get()
        if clear_all_messages:
            while not self._consume_queues[queue_name].empty():
                message = self._consume_queues[queue_name].get()

        return message

    def has_consume_queue(self, queue_name: str) -> bool:
        return queue_name in self._consume_queues

    def has_publish_queue(self, queue_name: str) -> bool:
        return queue_name in self._publish_queues

    def is_full(
            self,
            *,
            publish_queue_name: T.Optional[str] = None,
            consume_queue_name: T.Optional[str] = None
    ) -> bool:
        if publish_queue_name is None and consume_queue_name is None:
            raise ConfigurationError("None of params was got!")

        if publish_queue_name and consume_queue_name:
            raise ConfigurationError("Only one of params must set!")

        # if consume queue
        if consume_queue_name:
            if not self.has_consume_queue(consume_queue_name):
                raise ConfigurationError(f"Consume queue with name = '{consume_queue_name}' does not exist.")

            # TODO check if it's used anywhere
            return self._consume_queues[consume_queue_name].full()

        # if publish queue
        if not self.has_publish_queue(publish_queue_name):
            raise ConfigurationError(f"Publish queue with name = '{publish_queue_name}' does not exist.")

        for q in self._publish_queues[publish_queue_name]:
            if q.full():
                return True

        return False

    def is_empty(self, consume_queue_name: T.Optional[str] = None):
        """
        Checks inter-process queue is empty.
        It's only possible to check a consumer queue because there is no sense in checking publishing queues

        :param consume_queue_name: Name of an input queue. If it's none - check the only one queue
        that is set as input in config
        :type consume_queue_name: str
        :rtype: Bool
        """
        if len(self._consume_queues.keys()) == 0:
            raise ConfigurationError(f"Process \"{self.name}\" has no queues to read.")

        if consume_queue_name is None:
            if len(self._consume_queues.keys()) != 1:
                raise ConfigurationError(f"Process '{self.name}' has more than one read queue. Specify a consume queue name.")

            consume_queue_name = list(self._consume_queues.keys())[0]

        return self._consume_queues[consume_queue_name].empty()

    def _init_monitoring(self, name):
        """
        Initializes stack monitoring
        This feature will sample the stacks of all threads in the process for a period, then log them out
        """
        self._stack_monitor = StackMonitor(name)
        self._stack_monitor.start_monitoring()

    def respond_to(self, message: NamedMessage, data: T.Any) -> None:
        """
        Respond directly to the requesting process. This response should be awaited with the function wait_response.
        Computation block should be in try-except clause to prevent stucking the waiting process in case of exceptions.
        :param message: a message that provoked computations
        :type message: NamedMessage
        :param data: the response. Send ComputationFailure if an exception happend during the computations.
        """
        personal_id: str = message.id
        client_process: str = message.client_process
        self._system_queues[client_process].put(
            NamedMessage(id=personal_id, client_process=client_process, data=data)
        )

    def wait_response(self, request_id: str) -> T.Any:
        """
        Get a response after publishing a named message. The order of getting responses doesn't matter.
        It blocks the process until it gets the result.

        Example:
        P1:
        request1 = self.publish("compute_calibration", "robot_commands", named=True)
        request2 = self.publish("get_position", "robot_commands", named=True)

        position = self.wait_response(request2)
        calibration = self.wait_response(request1)

        P2:
        message = self.consume(robot_commands)
        try:
            assert (message is NamedMessage)

            if message.data == "get_position":
                self.respond_to(message, [1,1,1])
            if message.data == "compute_calibration":
                self.respond_to(message, [0, 2])
        except Exception as e:
            self.respond_to(message, ComputationFailure)
            raise e

        :param request_id: the result of publish(..., named=True)
        :type request_id: str
        Returns the computed data if everything is fine.
        Returns ComputationFailure if there was an exception during computations.
        """
        if request_id in self._received_named_messages:
            message: NamedMessage = self._received_named_messages[request_id]
            del self._received_named_messages[request_id]
            return message.data

        while True:
            # todo exception or logging?
            if len(self._received_named_messages) > 50:
                raise Exception(f"Overflow of personal messages for '{self.name}'!")

            message: NamedMessage = self._system_queues[self.name].get()
            if message.id == request_id:
                return message.data
            else:
                self._received_named_messages[message.id] = message.data

    def heartbeat(self, message: str):
        Thread(target=self.watcher.notify, daemon=True, args=(message,)).start()
