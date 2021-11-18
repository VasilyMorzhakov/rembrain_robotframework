import typing as T

from pydantic.main import BaseModel


class PersonalQueueData(BaseModel):
    id: str
    process_sender: str
    data: T.Any
