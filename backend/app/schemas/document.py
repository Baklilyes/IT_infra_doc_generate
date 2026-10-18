"""Pydantic schemas for Document Generation and Deliverables Management."""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class DocumentGenerateRequest(BaseModel):
    document_type: str = Field(..., description="'hld', 'lld', 'config_annexes', or 'commissioning'")
    file_format: str = Field("docx", description="'docx' or 'pdf'")
    use_ai: bool = Field(True, description="Enrich with local Ollama AI synthesis if available")
    version: str = Field("1.0", description="Document version string")


class DocumentResponse(BaseModel):
    id: str
    project_id: str
    document_type: str
    title: str
    version: str
    file_format: str
    file_size: int
    ai_enhanced: bool
    is_locked: bool
    created_at: datetime
    download_url: str = ""

    model_config = ConfigDict(from_attributes=True)


class DocumentStatusResponse(BaseModel):
    ai_status: dict
    total_generated: int
    allowed_types: list[str] = ["hld", "lld", "config_annexes", "commissioning"]
