from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict
from app.models.project import ProjectStatus, DocumentLanguage

# ---------------------------------------------------------
# Location Schemas
# ---------------------------------------------------------
class LocationBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=150)
    room: Optional[str] = Field(None, max_length=100)
    rack: Optional[str] = Field(None, max_length=50)
    notes: Optional[str] = None

class LocationCreate(LocationBase):
    pass

class LocationUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=150)
    room: Optional[str] = Field(None, max_length=100)
    rack: Optional[str] = Field(None, max_length=50)
    notes: Optional[str] = None

class LocationResponse(LocationBase):
    id: str
    site_id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------
# Site Schemas
# ---------------------------------------------------------
class SiteBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=150)
    code: Optional[str] = Field(None, max_length=50)
    address: Optional[str] = Field(None, max_length=255)
    city: Optional[str] = Field(None, max_length=100)
    country: Optional[str] = Field("France", max_length=100)
    notes: Optional[str] = None

class SiteCreate(SiteBase):
    pass

class SiteUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=150)
    code: Optional[str] = Field(None, max_length=50)
    address: Optional[str] = Field(None, max_length=255)
    city: Optional[str] = Field(None, max_length=100)
    country: Optional[str] = Field(None, max_length=100)
    notes: Optional[str] = None

class SiteResponse(SiteBase):
    id: str
    project_id: str
    locations_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class SiteDetailResponse(SiteBase):
    id: str
    project_id: str
    locations_count: int = 0
    locations: List[LocationResponse] = []
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------
# Project Schemas
# ---------------------------------------------------------
class ProjectBase(BaseModel):
    reference: str = Field(..., min_length=3, max_length=50, description="Référence unique du projet (ex. PRJ-2026-001)")
    name: str = Field(..., min_length=2, max_length=150, description="Nom explicite du projet")
    client_name: str = Field(..., min_length=2, max_length=150, description="Entreprise ou organisation cliente")
    description: Optional[str] = None
    scope: Optional[str] = None
    lead_name: str = Field(..., min_length=2, max_length=100, description="Responsable technique principal")
    contributors: Optional[str] = None
    status: ProjectStatus = ProjectStatus.DRAFT
    version: str = Field("1.0", max_length=20, description="Version du projet (ex: 1.0, 1.1)")
    parent_project_id: Optional[str] = None
    document_language: DocumentLanguage = DocumentLanguage.FR
    target_date: Optional[datetime] = None

class ProjectCreate(ProjectBase):
    initial_site_name: Optional[str] = Field(None, description="Nom optionnel d'un premier site créé automatiquement")

class ProjectUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=150)
    client_name: Optional[str] = Field(None, min_length=2, max_length=150)
    description: Optional[str] = None
    scope: Optional[str] = None
    lead_name: Optional[str] = Field(None, min_length=2, max_length=100)
    contributors: Optional[str] = None
    status: Optional[ProjectStatus] = None
    document_language: Optional[DocumentLanguage] = None
    target_date: Optional[datetime] = None
    is_archived: Optional[bool] = None

class ProjectDuplicateRequest(BaseModel):
    new_reference: str = Field(..., min_length=3, max_length=50, description="Nouvelle référence unique")
    new_name: Optional[str] = Field(None, description="Nouveau nom (si omis, suffixé avec ' - Copie')")

class ProjectResponse(ProjectBase):
    id: str
    is_archived: bool
    created_by_id: Optional[str] = None
    sites_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class ProjectDetailResponse(ProjectResponse):
    sites: List[SiteDetailResponse] = []

    model_config = ConfigDict(from_attributes=True)
