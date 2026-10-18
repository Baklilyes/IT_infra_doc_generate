"""Schemas for Import Job and Ingestion Workflows."""
from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field, ConfigDict


class ImportUploadResponse(BaseModel):
    job_id: str
    filename: str
    file_type: str
    headers: list[str] = Field(default_factory=list)
    sample_rows: list[dict[str, Any]] = Field(default_factory=list)
    suggested_mapping: dict[str, str] = Field(default_factory=dict)
    detected_target: str = "equipment"  # 'equipment' or 'network_segments' or 'cli'
    total_raw_rows: int = 0


class ImportPreviewRequest(BaseModel):
    mappings: dict[str, str] = Field(default_factory=dict)
    target_type: str = "equipment"  # 'equipment' or 'network_segments'


class ImportPreviewItem(BaseModel):
    row_number: int
    status: str  # 'valid', 'conflict', 'error'
    data: dict[str, Any]
    conflicts: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


class ImportPreviewResponse(BaseModel):
    job_id: str
    target_type: str
    total_items: int
    valid_count: int
    conflict_count: int
    error_count: int
    items: list[ImportPreviewItem] = Field(default_factory=list)


class ImportApplyRequest(BaseModel):
    conflict_resolution: str = "skip"  # 'skip', 'overwrite', 'create_new'


class ImportApplyResponse(BaseModel):
    job_id: str
    status: str
    created_count: int
    updated_count: int
    skipped_count: int
    error_count: int
    message: str


class ImportJobResponse(BaseModel):
    id: str
    project_id: str
    filename: str
    file_type: str
    target_type: str
    status: str
    total_rows: int
    created_count: int
    updated_count: int
    skipped_count: int
    error_count: int
    created_at: datetime
    applied_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)
