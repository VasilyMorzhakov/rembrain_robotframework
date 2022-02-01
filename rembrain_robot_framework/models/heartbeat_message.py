import typing as T

from pydantic import BaseModel


class HeartbeatMessage(BaseModel):
    """Struct for sending heartbeat message."""

    robot_name: str
    process_name: str
    process_class: str
    timestamp: str
    data: T.Any
