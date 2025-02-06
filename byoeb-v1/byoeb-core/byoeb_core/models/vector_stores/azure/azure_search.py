from pydantic import BaseModel, Field
from typing import Optional

class Metadata(BaseModel):
    source: Optional[str] = Field(None, description="Source of the chunk")

    # Optional fields
    update_timestamp: Optional[str] = Field(
        None,
        description="Timestamp when the chunk was last updated (optional)"
    )

    creation_timestamp: Optional[str] = Field(
        None,
        description="Timestamp when the chunk was created (optional)"
    )
    additional_metadata: Optional[dict] = Field(
        {},
        description="Additional metadata associated with the chunk"
    )

class AzureSearchNode(BaseModel):
    # Mandatory fields
    id: Optional[str] = Field(None, description="Unique identifier for the chunk")
    text: Optional[str] = Field(None, description="Content of the chunk")
    text_vector_3072: Optional[list] = Field(None, description="Vector representation of the text")
    metadata: Optional[Metadata] = Field(None, description="Metadata associated with the chunk")
    related_questions: Optional[dict] = Field({}, description="Related questions for the chunk")
