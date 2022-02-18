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

    def bson(self, *, encoded=True):
        data = self.dict(
            exclude={
                "data",
            }
        )
        bson_data = bson.dumps({"data": self.data, **data})
        return bson_data.encode("utf-8") if encoded else bson_data

    def bind_key(self):
        pass
