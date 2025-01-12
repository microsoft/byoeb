from pydantic import BaseModel, Field
from typing import Optional

class Chunk(BaseModel):
    # Mandatory fields
    chunk_id: str = Field(..., description="Unique identifier for the chunk")
    text: str = Field(..., description="Content of the chunk")
    metadata: dict = Field({}, description="Metadata associated with the chunk") 

    # Optional fields
    chunk_update_timestamp: Optional[str] = Field(
        None,
        description="Timestamp when the chunk was last updated (optional)"
    )

    chunk_creation_timestamp: Optional[str] = Field(
        None,
        description="Timestamp when the chunk was created (optional)"
    )