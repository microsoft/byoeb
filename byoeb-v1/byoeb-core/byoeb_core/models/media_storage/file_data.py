from pydantic import BaseModel, Field
from typing import Optional

class FileMetadata(BaseModel):
    file_name: str = Field(..., description="The file name")
    file_type: Optional[str] = Field(None, description="The file path")
    creation_time: str = Field(..., description="The created at timestamp")

class FileData(BaseModel):
    data: bytes = Field(..., description="The file data")
    metadata: Optional[FileMetadata] = Field(None, description="The file metadata")