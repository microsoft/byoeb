from pydantic import BaseModel, Field
from typing import List, Optional

class WhatsAppResponseStatus(BaseModel):
    status: str = Field(None, description="The status of the message")
    error: Optional[str] = Field(None, description="The error message if the message failed")

class Contact(BaseModel):
    input: str = Field(..., description="The input phone number with country code")
    wa_id: str = Field(..., description="The WhatsApp ID for the contact")

class MediaMessage(BaseModel):
    id: str = Field(..., description="The media ID on WhatsApp")

class Message(BaseModel):
    id: str = Field(..., description="The message ID on WhatsApp")
    message_status: Optional[str] = Field(None, description="The status of the message")

class WhatsAppResponse(BaseModel):
    response_status: WhatsAppResponseStatus = Field(None, description="The status of the response")
    messaging_product: str = Field(..., description="The messaging product, e.g., 'whatsapp'")
    contacts: List[Contact] = Field(..., description="List of contacts to whom the message is sent")
    messages: List[Message] = Field(..., description="List of messages being sent")
    media_message: Optional[MediaMessage] = Field(None, description="The media message being sent")