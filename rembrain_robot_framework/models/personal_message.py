import typing as T
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class PersonalMessage(BaseModel):
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
