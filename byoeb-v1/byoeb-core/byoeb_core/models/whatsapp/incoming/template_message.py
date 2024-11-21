from pydantic import BaseModel, Field
from typing import List, Optional

class Context(BaseModel):
    from_: str = Field(..., alias="from", description="The WhatsApp ID of the sender.")
    id: str = Field(..., description="The ID of the context message.")

class Button(BaseModel):
    payload: Optional[str] = Field(None, description="Payload data sent with the button interaction.")
    text: Optional[str] = Field(None, description="Text displayed on the button.")

class Message(BaseModel):
    context: Optional[Context] = Field(None, description="The context of the message.")
    from_: str = Field(..., alias="from", description="The WhatsApp ID of the sender.")
    id: str = Field(..., description="The ID of the incoming message.")
    timestamp: str = Field(..., description="The timestamp of the message.")
    type: str = Field(..., description="The type of the message (e.g., button).")
    button: Optional[Button] = Field(None, description="Details of the button interaction.")

class Profile(BaseModel):
    name: Optional[str] = Field(None, description="Name of the WhatsApp user.")

class Contact(BaseModel):
    profile: Optional[Profile] = Field(None, description="Profile information of the contact.")
    wa_id: str = Field(..., description="WhatsApp ID of the contact.")

class Metadata(BaseModel):
    display_phone_number: Optional[str] = Field(None, description="Display phone number of the business account.")
    phone_number_id: Optional[str] = Field(None, description="Phone number ID of the business account.")

class Value(BaseModel):
    messaging_product: str = Field(..., description="Messaging product being used (e.g., WhatsApp).")
    metadata: Metadata = Field(..., description="Metadata about the phone numbers.")
    contacts: List[Contact] = Field(..., description="List of contacts associated with the message.")
    messages: Optional[List[Message]] = Field(None, description="List of messages received.")

class Change(BaseModel):
    value: Value = Field(..., description="The main payload of the webhook event.")
    field: str = Field(..., description="The field related to the change.")

class Entry(BaseModel):
    id: str = Field(..., description="The ID of the WhatsApp Business Account entry.")
    changes: List[Change] = Field(..., description="List of changes included in the entry.")

class WhatsAppTemplateMessageBody(BaseModel):
    object: str = Field(..., description="The type of object related to the webhook (e.g., whatsapp_business_account).")
    entry: List[Entry] = Field(..., description="List of entries in the webhook payload.")
