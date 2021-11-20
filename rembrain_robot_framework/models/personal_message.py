import typing as T

from pydantic.main import BaseModel


class PersonalMessage(BaseModel):
    id: str
    client_process: str
    data: T.Any
