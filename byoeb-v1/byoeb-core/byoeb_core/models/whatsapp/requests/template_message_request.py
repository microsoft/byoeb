from pydantic import BaseModel, Field
from typing import Optional, List
from byoeb_core.models.whatsapp.message_context import WhatsappMessageReplyContext

class TemplateParameter(BaseModel):
    type: str = Field(..., description="Type of the parameter (e.g., 'text', 'image').")
    text: Optional[str] = Field(None, description="Text content of the parameter.")

class TemplateComponent(BaseModel):
    type: str = Field(..., description="Type of the component (e.g., 'body', 'action').")
    parameters: List[TemplateParameter] = Field(..., description="List of parameters for the component.")

class TemplateLanguage(BaseModel):
    code: str = Field(..., description="Language code for the template (e.g., 'en' for English).")

class Template(BaseModel):
    name: str = Field(..., description="Name of the template to use.")
    language: TemplateLanguage = Field(..., description="Language settings for the template.")
    components: Optional[List[TemplateComponent]] = Field(None, description="List of components for the template.")

class WhatsAppTemplateMessage(BaseModel):
    messaging_product: str = Field(..., description="Product identifier, typically 'whatsapp'.")
    to: str = Field(..., description="Recipient phone number in international format.")
    type: Optional[str] = Field(default="template", description="Type of the message, default is 'template'.")
    template: Template = Field(..., description="Template details including name and language.")
    context: Optional[WhatsappMessageReplyContext] = Field(None, description="The message context")
