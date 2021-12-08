import logging
import multiprocessing
import os
import ssl
import typing as T
from logging.handlers import QueueListener
from multiprocessing import Queue
from multiprocessing.context import BaseContext

import pika
from python_logging_rabbitmq import RabbitMQHandler

from rembrain_robot_framework.logger import JsonFormatter, LogHandler


def get_log_handler(project_description: dict, in_cluster: bool = True) -> T.Any:
    if in_cluster:
        if (
            "RABBIT_ADDRESS" not in os.environ
            or "@" not in os.environ["RABBIT_ADDRESS"]
        ):
            print("Warning, testing environment, web logging is not working")
            return None

        credentials, host = os.environ["RABBIT_ADDRESS"].split("@")
        user, password = credentials.replace("amqp://", "").split(":")
        connection_params = {}
        port = 5672

        if host != "rabbit-master/":
            stared_host: str = ".".join(["*"] + host.split(".")[-2:]).replace("/", "")
            context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            context.load_default_certs()
            connection_params = {
                "ssl_options": pika.SSLOptions(context, server_hostname=stared_host)
            }
            port = 5671

        return RabbitMQHandler(
            host=host[:-1],
            username=user,
            password=password,
            port=port,
            connection_params=connection_params,
            exchange=os.environ.get("LOG_EXCHANGE", "logstash"),
            declare_exchange=False,
            fields=project_description,
            formatter=JsonFormatter(),
        )
    else:
        if not (
            (
                "RRF_USERNAME" in os.environ
                and "RRF_PASSWORD" in os.environ
                and "WEBSOCKET_GATE_URL" in os.environ
            )
            or ("ML_NAME" in os.environ and "ML_PASSWORD" in os.environ)
        ):
            print("Warning, testing environment, web logging is not working")
            return None

        formatter = JsonFormatter()
        formatter.log_fields = project_description

        handler = LogHandler(fields=project_description)
        handler.setFormatter(formatter)
        return handler


def get_console_handler() -> logging.StreamHandler:
    console_handler = logging.StreamHandler()
    format_string = "%(levelname)s:%(name)s:%(message)s"
    console_handler.setFormatter(logging.Formatter(format_string))
    return console_handler


def setup_logging(
    project_description: dict, ctx: BaseContext, in_cluster: bool = True
) -> T.Tuple[Queue, QueueListener]:
    """
    Sets up a QueueListener that listens to the main logging queue and passes data to the handlers
    The handlers are generated here, there are three handlers:
        - Rabbit handler for in-cluster use
        - Websocket handler for robots and other processes running outside
        - Console logging
    Returns the queue for logging + the listener
    Don't forget to start the listener
    """
    log_queue = ctx.Queue()
    handlers = [get_console_handler()]

    out_handler = get_log_handler(project_description, in_cluster)
    if out_handler is not None:
        handlers.append(out_handler)

    listener = QueueListener(log_queue, *handlers)
    return log_queue, listener
