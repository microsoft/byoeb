from pydantic import BaseModel, Field
from typing import List, Optional

class ButtonReplyModel(BaseModel):
    id: Optional[str] = Field(None, description="Unique identifier for the button pressed.")
    title: Optional[str] = Field(None, description="Title of the button pressed.")

class ListReplyModel(BaseModel):
    id: Optional[str] = Field(None, description="Unique identifier for the list item selected.")
    title: Optional[str] = Field(None, description="Title of the list item selected.")
    description: Optional[str] = Field(None, description="Description of the list item selected.")

class InteractiveModel(BaseModel):
    type: Optional[str] = Field(None, description="Type of interactive message, e.g., 'button_reply' or 'list_reply'.")
    button_reply: Optional[ButtonReplyModel] = Field(None, description="Details of the button reply if the type is 'button_reply'.")
    list_reply: Optional[ListReplyModel] = Field(None, description="Details of the list reply if the type is 'list_reply'.")

class ContextModel(BaseModel):
    from_: Optional[str] = Field(None, alias="from", description="Sender's phone number.")
    id: Optional[str] = Field(None, description="Message ID of the original message context.")

class MessageModel(BaseModel):
    context: Optional[ContextModel] = Field(None, description="Context of the original message.")
    from_: Optional[str] = Field(None, alias="from", description="Sender's WhatsApp ID.")
    id: Optional[str] = Field(None, description="Unique identifier of the message.")
    timestamp: Optional[str] = Field(None, description="Timestamp of when the message was sent.")
    type: Optional[str] = Field(None, description="Type of message, e.g., 'interactive'.")
    interactive: Optional[InteractiveModel] = Field(None, description="Details of the interactive message.")

class ContactModel(BaseModel):
    profile: Optional[dict] = Field(None, description="Profile information of the contact.")
    wa_id: Optional[str] = Field(None, description="WhatsApp ID of the contact.")

class MetadataModel(BaseModel):
    display_phone_number: Optional[str] = Field(None, description="Display phone number of the business account.")
    phone_number_id: Optional[str] = Field(None, description="Unique identifier for the phone number.")

class ValueModel(BaseModel):
    messaging_product: Optional[str] = Field(None, description="Messaging product, e.g., 'whatsapp'.")
    metadata: Optional[MetadataModel] = Field(None, description="Metadata of the message.")
    contacts: Optional[List[ContactModel]] = Field(None, description="List of contacts involved in the message.")
    messages: Optional[List[MessageModel]] = Field(None, description="List of messages.")

class ChangeModel(BaseModel):
    value: Optional[ValueModel] = Field(None, description="Value object containing message details.")
    field: Optional[str] = Field(None, description="Field type, e.g., 'messages'.")

class EntryModel(BaseModel):
    id: Optional[str] = Field(None, description="Unique identifier for the entry.")
    changes: Optional[List[ChangeModel]] = Field(None, description="List of changes in the entry.")

class WhatsAppInteractiveMessageBody(BaseModel):
    object: Optional[str] = Field(None, description="Object type, e.g., 'whatsapp_business_account'.")
    entry: Optional[List[EntryModel]] = Field(None, description="List of entries in the message.")

    class Config:
        populate_by_name = True
