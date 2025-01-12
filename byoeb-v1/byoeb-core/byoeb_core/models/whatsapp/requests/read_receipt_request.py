from pydantic import BaseModel, Field
from typing import Optional, List

class WhatsAppReadMessage(BaseModel):
    messaging_product: str = Field(..., description="Product identifier, typically 'whatsapp'.")
    status: str = Field("read", description="Status of the message.")
    message_id: str = Field(..., description="Unique identifier of the message.")