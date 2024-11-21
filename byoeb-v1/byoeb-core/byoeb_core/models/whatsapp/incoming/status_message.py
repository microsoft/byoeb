from pydantic import BaseModel
from typing import Optional, List, Dict


class ErrorData(BaseModel):
    details: Optional[str]


class Error(BaseModel):
    code: Optional[int]
    title: Optional[str]
    message: Optional[str]
    error_data: Optional[ErrorData]


class Origin(BaseModel):
    type: Optional[str]


class Conversation(BaseModel):
    id: Optional[str]
    expiration_timestamp: Optional[str]
    origin: Optional[Origin]


class Pricing(BaseModel):
    billable: Optional[bool]
    pricing_model: Optional[str]
    category: Optional[str]


class Status(BaseModel):
    id: Optional[str]
    status: Optional[str]
    timestamp: Optional[str]
    recipient_id: Optional[str]
    conversation: Optional[Conversation]
    pricing: Optional[Pricing]
    errors: Optional[List[Error]]  # Added errors field


class Metadata(BaseModel):
    display_phone_number: Optional[str]
    phone_number_id: Optional[str]


class Value(BaseModel):
    messaging_product: Optional[str]
    metadata: Optional[Metadata]
    statuses: Optional[List[Status]]


class Change(BaseModel):
    value: Optional[Value]
    field: Optional[str]


class Entry(BaseModel):
    id: Optional[str]
    changes: Optional[List[Change]]


class WhatsAppStatusMessageBody(BaseModel):
    object: Optional[str]
    entry: Optional[List[Entry]]
