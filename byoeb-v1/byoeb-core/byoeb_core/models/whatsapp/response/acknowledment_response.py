from pydantic import BaseModel, Field
from typing import Optional
from byoeb_core.models.whatsapp.response.message_response import WhatsAppResponseStatus

class ErrorData(BaseModel):
    message: Optional[str] = Field(None, description="The error message")
    code: Optional[int] = Field(None, description="The error code")
    type: Optional[str] = Field(None, description="The error type")

class WhatsAppAcknowledgment(BaseModel):
    response_status: Optional[WhatsAppResponseStatus] = Field(None, description="The status of the response")
    success: Optional[bool] = Field(None, description="Whether the read receipt was successful")
    error: Optional[ErrorData] = Field(None, description="Error details if the read receipt failed")
