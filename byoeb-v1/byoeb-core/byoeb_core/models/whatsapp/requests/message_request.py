from pydantic import BaseModel, Field
from typing import Optional
from byoeb_core.models.whatsapp.message_context import WhatsappMessageReplyContext

class Text(BaseModel):
    body: str = Field(..., description="The message body text")

class Reaction(BaseModel):
    message_id: Optional[str] = Field(None, description="The message id to which the reaction is sent")
    emoji: Optional[str] = Field(..., description="The emoji to send as a reaction")

class Audio(BaseModel):
    id: str = Field(..., description="The audio id")

class WhatsAppMessage(BaseModel):
    messaging_product: str = Field(None, description="The messaging product, e.g., 'whatsapp'")
    to: str = Field(..., description="The recipient's phone number with country code")
    text: Optional[Text] = Field(None, description="The message content")
    type: Optional[str] = Field(None, description="The type of message")
    reaction: Optional[Reaction] = Field(None, description="The reaction to send")
    audio: Optional[Audio] = Field(None, description="The audio to send")
    context: Optional[WhatsappMessageReplyContext] = Field(None, description="The message context")