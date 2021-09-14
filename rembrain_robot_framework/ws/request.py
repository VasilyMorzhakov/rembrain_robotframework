import typing as T

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
    """

    command: str
    exchange: str
    robot_name: str
    access_token: str = ""
    username: str = ""
    password: str = ""
    message: T.Any = None
