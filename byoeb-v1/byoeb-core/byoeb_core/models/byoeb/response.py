from pydantic import BaseModel
from enum import Enum
from typing import Any

class ByoebStatusCodes(Enum):
    """
    An enumeration of HTTP status codes.

    Attributes:
        OK (int): The status code for a successful request.
        BAD_REQUEST (int): The status code for a bad request.
        UNAUTHORIZED (int): The status code for an unauthorized request.
        FORBIDDEN (int): The status code for a forbidden request.
        NOT_FOUND (int): The status code for a not found request.
        INTERNAL_SERVER_ERROR (int): The status code for an internal server error.
    """
    OK = 200
    BAD_REQUEST = 400
    UNAUTHORIZED = 401
    FORBIDDEN = 403
    NOT_FOUND = 404
    INTERNAL_SERVER_ERROR = 500

class ByoebResponseModel(BaseModel):
    """
    A Pydantic model for modeling a response.

    Attributes:
        message (str): The message of the response.
        status_code (int): The HTTP status code of the response.
    """
    message: Any
    status_code: int