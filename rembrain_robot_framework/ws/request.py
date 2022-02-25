import typing as T

import bson
from pika.exchange_type import ExchangeType
from pydantic.main import BaseModel


class WsRequest(BaseModel):
    """
    Params for request to websocket:
    command:  WsCommandType enum
    exchange:  RabbitMQ exchange
    robot_name:  robot name
    access_token:  auth token - if it does not exist - there must be 'username' and 'password' params.
    username:  username - only access_token does not exist
    password:  password - only access_token does not exist
    message:  message for request
    exchange:  exchange name
    exchange_type:  exchange type(allowed values: 'fanout', 'topic')
    """

    command: str
    robot_name: str
    access_token: str = ""  # todo maybe use  Field(..., alias='accessToken') ?
    username: str = ""
    password: str = ""
    message: T.Any = None

    exchange: str
    exchange_type: str = ExchangeType.fanout.value
    exchange_bind_key: str = ""

    def bson(self, encoded=True):
        data = self.dict(
            exclude={
                "message",
            }
        )
        bson_data = bson.dumps({"message": self.message, **data})
        return bson_data.encode("utf-8") if encoded else bson_data
