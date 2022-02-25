import typing as T
from uuid import UUID, uuid4

import bson
from pydantic import BaseModel, Field


class Request(BaseModel):
    """
    Personal struct for sending messages thorough queues.
    Args:
        uid: Unique value for request.
        **[Required]** client_process: Name of process, which have sent request and which are waiting response.
        **[Required]** data: Any serialized data
    """

    uid: UUID = Field(default_factory=uuid4)
    client_process: str = Field(min_length=1)
    service_name: str = ""
    data: T.Any

    def to_bson(self) -> bytes:
        return bson.BSON.encode(self.dict())

    @classmethod
    def from_bson(cls, bytes_data):
        return cls(**bson.BSON.decode(bytes_data))
