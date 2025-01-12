from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum

class ByoebMessageStatus(BaseModel):
    channel_type: Optional[str] = Field(None, description="The communication channel type", example="whatsapp")
    message_category: Optional[str] = Field(None, description="The category of the message", example="notification")
    message_id: Optional[str] = Field(None, description="Unique identifier for the message", example="msg12345")
    status: Optional[str] = Field(None, description="The current status of the message", example="delivered")
    incoming_timestamp: Optional[int] = Field(None, description="Timestamp when the message was sent or received", example=1633028300)
    recipient_id: Optional[str] = Field(None, description="Unique identifier for the recipient", example="user123")
    phone_number_id: Optional[str] = Field(None, description="Phone number ID of the sender or receiver", example="918837701828")