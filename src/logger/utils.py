import logging
import os
import ssl
import typing as T

import pika
from python_logging_rabbitmq import RabbitMQHandler

from rembrain_robotframework.src.logger.formatter import JsonFormatter
from rembrain_robotframework.src.logger.handler import LogHandler


def get_log_handler(project_description: dict, in_cluster: bool = True) -> T.Any:
    if in_cluster:
        if "RABBIT_ADDRESS" not in os.environ or "@" not in os.environ["RABBIT_ADDRESS"]:
            print("Warning, testing environment, web logging is not working")
            return logging.StreamHandler()

        credentials, host = os.environ["RABBIT_ADDRESS"].split("@")
        user, password = credentials.replace("amqp://", "").split(":")
        connection_params = {}
        port = 5672

        if host != "rabbit-master/":
            stared_host: str = ".".join(["*"] + host.split(".")[-2:]).replace("/", "")
            context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            context.load_default_certs()
            connection_params = {"ssl_options": pika.SSLOptions(context, server_hostname=stared_host)}
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
                ("ROBOT_NAME" in os.environ and "ROBOT_PASSWORD" in os.environ)
                or ("ML_NAME" in os.environ and "ML_PASSWORD" in os.environ)
        ):
            print("Warning, testing environment, web logging is not working")
            return logging.StreamHandler()

        formatter = JsonFormatter()
        formatter.log_fields = project_description

        handler = LogHandler(fields=project_description)
        handler.setFormatter(formatter)
        return handler


def set_logger(project_description: dict, in_cluster: bool = True) -> None:
    main_logger: logging.Logger = logging.getLogger()
    main_logger.setLevel(os.environ.get("LOGLEVEL", "INFO").upper())

    # if it into cluster - it just uses rabbit directly, else - it uses web sockets.
    if in_cluster:
        if "RABBIT_ADDRESS" not in os.environ:
            print("No rabbit address is supplied for this process, logging is not started.")
            return

        logging.getLogger("pika").setLevel(logging.WARNING)

    logging.root.addHandler(get_log_handler(project_description, in_cluster))
