from pydantic import BaseModel, Field
from enum import Enum
from typing import List, Optional, Dict, Any
from byoeb_core.models.byoeb.user import User

class MessageTypes(Enum):
    REGULAR_TEXT = "regular_text"
    REGULAR_AUDIO = "regular_audio"
    TEMPLATE_BUTTON = "template_button"                                   
    INTERACTIVE_BUTTON = "interactive_button_reply"
    INTERACTIVE_LIST = "interactive_list_reply"

class MediaContext(BaseModel):
    media_id: str = Field(..., description="Unique identifier for the media", example="media12345")
    mime_type: Optional[str] = Field(None, description="MIME type of the media", example="image/jpeg")
    media_type: Optional[str] = Field(None, description="Type of the media (e.g., image, video, audio)", example="image")
    media_url: Optional[str] = Field(None, description="URL where the media is hosted", example="http://example.com/media12345")

class MessageContext(BaseModel):
    message_id: Optional[str] = Field(None, description="Unique identifier for the message", example="msg12345")
    message_type: Optional[str] = Field(None, description="Type of the message (e.g., text, template, media)", example="text")
    message_source_text: Optional[str] = Field(None, description="Original text of the message", example="Hello, how can I help?")
    message_english_text: Optional[str] = Field(None, description="Translated English version of the message", example="Hello, how can I help?")
    media_info: Optional[MediaContext] = Field(None, description="Information about media attached to the message")
    additional_info: Optional[Dict[str, Any]] = Field(None, description="Any additional information related to the message")

class ReplyContext(BaseModel):
    reply_id: Optional[str] = Field(None, description="Unique identifier of the message to reply", example="reply12345")
    reply_type: Optional[str] = Field(None, description="Type of the message to reply", example="acknowledgment")
    reply_source_text: Optional[str] = Field(None, description="Original text of message to reply", example="I received your message")
    reply_english_text: Optional[str] = Field(None, description="Translated English version of message to reply", example="I received your message")
    media_info: Optional[MediaContext] = Field(None, description="Information about media attached")
    message_category: Optional[str] = Field(None, description="Category of the message to reply", example="notification")
    additional_info: Optional[Dict[str, Any]] = Field(None, description="Any additional information related to the message to reply")

class ByoebMessageContext(BaseModel):
    channel_type: str = Field(..., description="The communication channel type (e.g., whatsapp, telegram)", example="whatsapp")
    message_category: Optional[str] = Field(None, description="Category of the message (e.g., notification, user-query)", example="notification")
    user: Optional[User] = Field(None, description="User information related to the message")
    message_context: Optional[MessageContext] = Field(None, description="Context of the incoming message")
    reply_context: Optional[ReplyContext] = Field(None, description="Context of the reply to the message")
    cross_conversation_id: Optional[str] = Field(None, description="Cross-conversation ID for multi-platform communication", example="conversation12345")
    cross_conversation_context: Optional[Dict[str, Any]] = Field(None, description="Context of the cross-conversation message")
    incoming_timestamp: Optional[int] = Field(None, description="Timestamp when the message was received", example=1633028300)
    outgoing_timestamp: Optional[int] = Field(None, description="Timestamp when the message was sent", example=1633028301)