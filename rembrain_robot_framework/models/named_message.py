import typing as T

from pydantic.main import BaseModel


class NamedMessage(BaseModel):
    id: str
    client_process: str
    data: T.Any
