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
    client_process: str
    data: T.Any

    def to_bson(self):
        bson_data = bson.dumps(self.dict())
        return bson_data.encode("utf-8")

    @classmethod
    def from_bson(cls, bytes_data):
        data = bson.loads(bytes_data.decode("utf-8"))
        return cls(**data)
