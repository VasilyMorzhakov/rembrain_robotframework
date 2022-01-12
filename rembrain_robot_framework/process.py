import logging
import os
import typing as T
from collections import namedtuple
from multiprocessing import Queue
from uuid import UUID

from rembrain_robot_framework.models.personal_message import PersonalMessage
from rembrain_robot_framework.utils import ConfigurationError
from rembrain_robot_framework.services.stack_monitor import StackMonitor


class RobotProcess:
    # TODO: add doctrings for this parameters
    def __init__(
        self,
        name: str,
        shared_objects: dict,
        consume_queues: T.Dict[str, Queue],
        publish_queues: T.Dict[str, T.List[Queue]],
        system_queues: T.Dict[str, Queue],
        watcher_queue: T.Optional[Queue],
        *args,
        **kwargs,
    ):
        self.name: str = name

        # queues for reading
        self._consume_queues: T.Dict[str, Queue] = consume_queues
        # queues for writing
        self._publish_queues: T.Dict[str, T.List[Queue]] = publish_queues

        self._shared: T.Any = namedtuple("_", shared_objects.keys())(**shared_objects)

        self._system_queues: T.Dict[str, Queue] = system_queues
        self._received_personal_messages = {}

        # in case of exception these queues are cleared
        self.queues_to_clear: T.List[str] = []
        self.log = logging.getLogger(f"{self.__class__.__name__} ({self.name})")

        self._stack_monitor: T.Optional[StackMonitor] = None
        if "monitoring" in kwargs and kwargs["monitoring"]:
            self._init_monitoring(self.name)

        self.watcher_queue = watcher_queue

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

    # todo isn't it's better just to force calling super().free_resources in overridden methods?
    def close_objects(self) -> None:
        """It can be overridden in process implementation."""
        pass

    def clear_queues(self) -> None:
        """
        Clear all messages in queues from self.queues_to_clear. Usually this is called when a process stops/restarts.
        :return:
        :rtype:
        """
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

    def publish(
        self,
        message: T.Any,
        queue_name: T.Optional[str] = None,
        clear_on_overflow: bool = False,
    ) -> None:
        """
        Sends message to all processes that are configured to listen to the queue_name.
        If there are several processes for listening then everyone will receive a copy of the message.

        :param message: Any serialized data to transfer over interprocess queues.

        :param queue_name: Name of the queue to send message to.
        If there is only one output queue it's possible to omit this argument,
        it will pick this single queue by default.
        :type queue_name: Optional[str]

        :param bool clear_on_overflow: If this parameter is set and a queue to write is full,
        publish will empty the queue before publishing of new messages.

        :return: None

        :raise: ConfigurationError: if number of queues != 1 and queue name was not given
        """
        if len(self._publish_queues.keys()) == 0:
            self.log.error(f'Process "{self.name}" has no queues to write.')
            raise ConfigurationError(
                f"Publish called with 0 output queues for process {self.name}"
            )

        if queue_name is None:
            if len(self._publish_queues.keys()) != 1:
                self.log.error(
                    f'Process "{self.name}" has more than one write queue. Specify a write queue name.'
                )
                raise ConfigurationError(
                    f"Publish called with >1 output queues for process {self.name}"
                )
            queue_name = list(self._publish_queues.keys())[0]

        for q in self._publish_queues[queue_name]:
            if clear_on_overflow:
                while q.full():
                    q.get()
            q.put(message)

    def consume(
        self, queue_name: T.Optional[str] = None, clear_all_messages: bool = False
    ) -> T.Any:
        if len(self._consume_queues.keys()) == 0:
            raise ConfigurationError(
                f"Consume called with 0 input queues for process {self.name}"
            )

        if queue_name is None:
            if len(self._consume_queues.keys()) != 1:
                raise ConfigurationError(
                    f"Consume called with >1 input queues for process {self.name}"
                )

            queue_name = list(self._consume_queues.keys())[0]

        message: str = self._consume_queues[queue_name].get()
        if clear_all_messages:
            while not self._consume_queues[queue_name].empty():
                message = self._consume_queues[queue_name].get()

        return message

    def publish_personal(
        self,
        message: T.Any,
        queue_name: T.Optional[str] = None,
        clear_on_overflow: bool = False,
    ) -> UUID:
        """
        Wraps 'message' as PersonalMessage(adding current process name and message id for the
        receiving code in order to be able to respond) and then sends
        to all processes that are configured to listen queue_name.
        If there are several processes for listening then everyone will receive a copy of the message.

        :param message: Any serialized data to transfer over interprocess queues.

        :param queue_name: Name of the queue to send message to.
        If there is only one output queue it's possible to omit this argument,
        it will pick this single queue by default.
        :type queue_name: Optional[str]

        :param bool clear_on_overflow: If this parameter is set and a queue to write is full,
        publish will empty the queue before publishing of new messages.

        :return: message id.
        :rtype: str

        :raise: ConfigurationError: if number of queues != 1 and queue name was not given
        """
        message = PersonalMessage(client_process=self.name, data=message)
        self.publish(message, queue_name, clear_on_overflow)
        return message.uid

    def consume_personal(
        self, queue_name: T.Optional[str] = None, clear_all_messages: bool = False
    ) -> PersonalMessage:
        return self.consume(queue_name, clear_all_messages)

    def has_consume_queue(self, queue_name: str) -> bool:
        return queue_name in self._consume_queues

    def has_publish_queue(self, queue_name: str) -> bool:
        return queue_name in self._publish_queues

    def is_full(
        self,
        *,
        publish_queue_name: T.Optional[str] = None,
        consume_queue_name: T.Optional[str] = None,
    ) -> bool:
        if publish_queue_name is None and consume_queue_name is None:
            raise ConfigurationError("None of params was got!")

        if publish_queue_name and consume_queue_name:
            raise ConfigurationError("Only one of params must set!")

        # if consume queue
        if consume_queue_name:
            if not self.has_consume_queue(consume_queue_name):
                raise ConfigurationError(
                    f"Consume queue with name = '{consume_queue_name}' does not exist."
                )

            # TODO check if it's used anywhere
            return self._consume_queues[consume_queue_name].full()

        # if publish queue
        if not self.has_publish_queue(publish_queue_name):
            raise ConfigurationError(
                f"Publish queue with name = '{publish_queue_name}' does not exist."
            )

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
            raise ConfigurationError(f'Process "{self.name}" has no queues to read.')

        if consume_queue_name is None:
            if len(self._consume_queues.keys()) != 1:
                raise ConfigurationError(
                    f"Process '{self.name}' has more than one read queue. Specify a consume queue name."
                )

            consume_queue_name = list(self._consume_queues.keys())[0]

        return self._consume_queues[consume_queue_name].empty()

    def respond_to(
        self, personal_message_uid: UUID, client_process: str, data: T.Any
    ) -> None:
        """
        Respond directly to the requesting process.
        This response should be awaited with the function wait_response.
        Computation block should be in try-except clause
        to prevent stuck the waiting process in case of exceptions.

        :param UUID personal_message_uid: a message that provoked computations
        :param str client_process: the process which sent response and which have been waiting response.
        :param data: the response. Send

        :return None
        """
        self._system_queues[client_process].put(
            PersonalMessage(
                uid=personal_message_uid, client_process=client_process, data=data
            )
        )

    def wait_response(self, personal_message_uid: UUID) -> T.Any:
        """
        Get a response after publishing a personal message. The order of getting responses doesn't matter.
        It blocks the process until it gets the result.

        Example:
        P1:
        personal_message_uid_1 = self.publish_personal(message="compute_calibration", queue_name="robot_commands")
        personal_message_uid_2 = self.publish_personal(message="get_position", queue_name="robot_commands")

        position = self.wait_response(personal_message_uid_2)
        calibration = self.wait_response(personal_message_uid_1)

        P2:
        personal_message:PersonalMessage = self.consume_personal(queue_name="robot_commands")

        if personal_message.data == "get_position":
            self.respond_to(personal_message.uid, personal_message.client_process, [1,1,1])

        if personal_message.data == "compute_calibration":
            self.respond_to(personal_message.uid, [0, 2])

        :param UUID personal_message_uid: the result of publish_personal(...)
        :returns the computed data
        """
        if personal_message_uid in self._received_personal_messages:
            personal_message: PersonalMessage = self._received_personal_messages[
                personal_message_uid
            ]
            del self._received_personal_messages[personal_message_uid]
            return personal_message.data

        while True:
            if len(self._received_personal_messages) > 50:
                raise Exception(f"Overflow of personal messages for '{self.name}'!")

            personal_message: PersonalMessage = self._system_queues[self.name].get()
            if personal_message.uid == personal_message_uid:
                return personal_message.data

            self._received_personal_messages[
                personal_message.uid
            ] = personal_message.data

    def heartbeat(self, message: str):
        if self.watcher_queue:
            # todo what about blocking thread?
            self.watcher_queue.put(message)

    @staticmethod
    def get_arg_with_env_fallback(
        kwargs: T.Dict[str, T.Any], key: str, fallback_env_var: str
    ) -> T.Any:
        """
        Gets argument for the process from the kwargs by the `key`.
        If it doesn't exist, tries to get it from the environment using `fallback_env_var`
        """
        if key in kwargs:
            return kwargs[key]

        if fallback_env_var not in os.environ:
            raise RuntimeError(
                f"Couldn't get argument value of '{key}' for the process and there was no env var '{fallback_env_var}'"
            )

        return os.environ[fallback_env_var]

    def _init_monitoring(self, name):
        """
        Initializes stack monitoring
        This feature will sample the stacks of all threads in the process for a period, then log them out
        """
        self._stack_monitor = StackMonitor(name)
        self._stack_monitor.start_monitoring()
