"""Schemas for SVG Architecture Diagrams."""
from datetime import datetime
from pydantic import BaseModel, Field


class DiagramResponse(BaseModel):
    diagram_type: str  # 'physical', 'logical', 'flows'
    title: str
    svg: str
    elements_count: int = 0
    generated_at: datetime = Field(default_factory=datetime.utcnow)


class DiagramExportRequest(BaseModel):
    format: str = "svg"  # 'svg', 'png'
    theme: str = "modern"
