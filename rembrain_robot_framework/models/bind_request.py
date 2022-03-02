from typing import Union

import bson
from pydantic import BaseModel

from rembrain_robot_framework.models.request import Request


class BindRequest(BaseModel):
    """
    Personal struct for sending messages thorough queues.
    Args:
        **[Required]** bind_key: Exchange bind key.
        **[Required]** item: Request item in bytes
    """

    bind_key: str
    request: Union[Request, bytes]

    def to_bson(self):
        data = self.dict(
            exclude={
                "request",
            }
        )

        request = self.request
        if isinstance(self.request, Request):
            request = self.request.dict()

        # 'request' is either dict or bytes
        return bson.BSON.encode({"request": request, **data})

    @classmethod
    def from_bson(cls, bytes_data):
        data: dict = bson.BSON.decode(bytes_data)

        print("REQ: ", data)
        request_data = data["request"]
        if isinstance(request_data, bytes):
            request = Request.from_bson(request_data)
        else:
            # if it's dict
            request = Request(**request_data)

        return cls(bind_key=data["bind_key"], request=request)
