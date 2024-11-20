from typing import List, Optional
from pydantic import BaseModel, Field
from byoeb_core.models.byoeb.user import UserInfo

class MediaInfo(BaseModel):
    media_id: str
    media_type: str
    media_url: str

class MessageInfo(BaseModel):
    message_id: str
    message_type: str
    conversation_id: str
    cross_conversation_id: str
    message_source_text: str
    message_english_text: str
    media_info: Optional[MediaInfo]
    additional_info: Optional[dict]

class ReplyInfo(BaseModel):
    reply_id: str
    orig_reply_source_text: str
    orig_reply_english_text: str
    expert_correction_text: str
    correct_reply_source_text: str
    correct_reply_english_text: str

class ByoebMessageConext(BaseModel):
    """
    A Pydantic model for modeling a message context.
    
    Attributes:
        from_ (str): The WhatsApp ID of the original sender.
        id (str): The ID of the original message.
    """
    context_id: str
    channel_type: str
    user_info: Optional[UserInfo]
    message_info: Optional[MessageInfo]
    reply_info: Optional[ReplyInfo]
    cross_conversation_id: str