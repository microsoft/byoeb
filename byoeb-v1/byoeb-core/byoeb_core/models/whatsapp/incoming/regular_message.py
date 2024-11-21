from typing import List, Optional
from pydantic import BaseModel, Field

class Profile(BaseModel):
    name: Optional[str] = Field(None, description="Name of the contact's profile")

class Contact(BaseModel):
    profile: Optional[Profile] = Field(None, description="Profile details of the contact")
    wa_id: Optional[str] = Field(None, description="WhatsApp ID of the contact")

class TextMessage(BaseModel):
    body: Optional[str] = Field(None, description="Text body of the message")

class Context(BaseModel):
    from_: Optional[str] = Field(None, alias="from", description="WhatsApp ID of the original sender")
    id: Optional[str] = Field(None, description="ID of the original message")

class Audio(BaseModel):
    id: Optional[str] = Field(None, description="ID of the audio file")
    mime_type: Optional[str] = Field(None, description="MIME type of the audio file")
    sha256: Optional[str] = Field(None, description="SHA-256 hash of the audio file")
    voice: Optional[bool] = Field(None, description="Indicates if the audio is a voice note")

class Message(BaseModel):
    context: Optional[Context] = Field(None, description="Context of the message, if it is a reply")
    from_: Optional[str] = Field(None, alias="from", description="WhatsApp ID of the sender")
    id: Optional[str] = Field(None, description="Unique ID of the message")
    timestamp: Optional[str] = Field(None, description="Timestamp of the message")
    type: Optional[str] = Field(None, description="Type of the message (e.g., text, audio)")
    text: Optional[TextMessage] = Field(None, description="Details of a text message")
    audio: Optional[Audio] = Field(None, description="Details of an audio message")

class Metadata(BaseModel):
    display_phone_number: Optional[str] = Field(None, description="The phone number displayed to users")
    phone_number_id: Optional[str] = Field(None, description="ID of the phone number associated with the WhatsApp Business account")

class Value(BaseModel):
    contacts: Optional[List[Contact]] = Field(None, description="List of contacts involved in the message")
    messages: Optional[List[Message]] = Field(None, description="List of messages sent or received")
    messaging_product: Optional[str] = Field(None, description="The messaging product (e.g., WhatsApp)")
    metadata: Optional[Metadata] = Field(None, description="Metadata associated with the message")

class Change(BaseModel):
    field: Optional[str] = Field(None, description="Field that was changed (e.g., messages)")
    value: Optional[Value] = Field(None, description="Details of the change")

class Entry(BaseModel):
    changes: Optional[List[Change]] = Field(None, description="List of changes in this entry")
    id: Optional[str] = Field(None, description="ID of the entry")

class WhatsAppRegularMessageBody(BaseModel):
    entry: Optional[List[Entry]] = Field(None, description="List of entries in the webhook payload")
    object: Optional[str] = Field(None, description="Type of object that generated the webhook (e.g., whatsapp_business_account)")

    class Config:
        populate_by_name = True