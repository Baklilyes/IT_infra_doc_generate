"""Pydantic schemas for Consistency Engine and Audit Overrides."""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class FindingResponse(BaseModel):
    id: str
    rule_code: str
    rule_title: str
    category: str
    severity: str  # 'blocking', 'warning', 'info'
    target_type: str
    target_id: str
    target_name: str
    message: str
    recommendation: str
    is_overridden: bool = False
    override_id: Optional[str] = None
    override_justification: Optional[str] = None


class ConsistencyReportResponse(BaseModel):
    id: str
    project_id: str
    status: str  # 'passed', 'warnings_only', 'failed'
    blocking_count: int
    warning_count: int
    info_count: int
    resolved_count: int
    total_findings: int
    findings: list[FindingResponse] = Field(default_factory=list)
    created_at: datetime
    executed_by_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ConsistencyOverrideCreate(BaseModel):
    rule_code: str = Field(..., description="Code technique de la règle (ex. IP_DUPLICATE)")
    target_id: str = Field(..., description="ID ou identifiant de l'élément cible")
    target_type: str = Field(..., description="Type d'entité cible")
    severity: str = Field(..., description="Sévérité (blocking, warning)")
    justification: str = Field(..., min_length=10, description="Justification technique obligatoire et détaillée")


class ConsistencyOverrideResponse(BaseModel):
    id: str
    project_id: str
    rule_code: str
    target_id: str
    target_type: str
    severity: str
    justification: str
    is_active: bool
    created_at: datetime
    overridden_by_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class CanPublishResponse(BaseModel):
    project_id: str
    can_publish: bool
    status: str
    blocking_count: int
    unjustified_warnings: int
    message: str
