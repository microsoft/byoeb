from pydantic import BaseModel, Field
from typing import Optional

class WhatsappMessageReplyContext(BaseModel):
    message_id: str = Field(..., description="The message id to which the reply is sent")

# Example usage
# message_context = WhatsappMessageContext(from_="1234567890", id="msgid123")
# print(message_context.dict(by_alias=True))and 
