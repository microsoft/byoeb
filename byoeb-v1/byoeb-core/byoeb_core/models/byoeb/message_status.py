from pydantic import BaseModel
from enum import Enum

class ByoebMessageStatus(BaseModel):
    channel_type: str
    message_id: str
    status: str
    timestamp: int
    recipient_id: str
    phone_number_id: str