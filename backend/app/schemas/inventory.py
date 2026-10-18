from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, ConfigDict
from app.models.equipment import EquipmentCategory, InstallationStatus, VerificationStatus

class EquipmentBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=150, description="Hostname ou identifiant")
    category: EquipmentCategory
    subcategory: Optional[str] = Field(None, max_length=100)
    manufacturer: Optional[str] = Field(None, max_length=100)
    model: Optional[str] = Field(None, max_length=100)
    serial_number: Optional[str] = Field(None, max_length=100)
    management_ip: Optional[str] = Field(None, max_length=50)
    firmware_version: Optional[str] = Field(None, max_length=100)
    role: Optional[str] = Field(None, max_length=150)
    installation_status: InstallationStatus = InstallationStatus.IN_SERVICE
    verification_status: VerificationStatus = VerificationStatus.VERIFIED
    data_source: str = "manual"
    notes: Optional[str] = None
    site_id: Optional[str] = None
    location_id: Optional[str] = None
    specific_attributes: Optional[Dict[str, Any]] = Field(default_factory=dict)

class EquipmentCreate(EquipmentBase):
    pass

class EquipmentUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=150)
    category: Optional[EquipmentCategory] = None
    subcategory: Optional[str] = None
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    serial_number: Optional[str] = None
    management_ip: Optional[str] = None
    firmware_version: Optional[str] = None
    role: Optional[str] = None
    installation_status: Optional[InstallationStatus] = None
    verification_status: Optional[VerificationStatus] = None
    notes: Optional[str] = None
    site_id: Optional[str] = None
    location_id: Optional[str] = None
    specific_attributes: Optional[Dict[str, Any]] = None

class EquipmentResponse(EquipmentBase):
    id: str
    project_id: str
    site_name: Optional[str] = None
    location_name: Optional[str] = None
    interfaces_count: int = 0
    configurations_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class DuplicateFinding(BaseModel):
    field: str
    value: str
    equipment_ids: List[str]
    equipment_names: List[str]
