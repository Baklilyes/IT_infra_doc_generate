from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict
from app.models.network import InterfaceType, InterfaceMode
from app.models.equipment import VerificationStatus

# -------------------------------------------------------------
# Interface Schemas
# -------------------------------------------------------------
class InterfaceBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="Nom de l'interface (ex. Gi1/0/1)")
    interface_type: InterfaceType = InterfaceType.PHYSICAL
    mac_address: Optional[str] = Field(None, max_length=50)
    ip_address: Optional[str] = Field(None, max_length=50)
    subnet_mask: Optional[str] = Field(None, max_length=50)
    mode: InterfaceMode = InterfaceMode.ACCESS
    access_vlan: Optional[int] = Field(None, ge=1, le=4094)
    allowed_vlans: Optional[str] = Field(None, max_length=255)
    speed_duplex: Optional[str] = Field(None, max_length=50)
    admin_status: str = Field("up", max_length=20)
    operational_status: Optional[str] = Field(None, max_length=20)
    description: Optional[str] = Field(None, max_length=255)
    connected_equipment_id: Optional[str] = None
    connected_interface_name: Optional[str] = Field(None, max_length=100)
    link_type: Optional[str] = Field(None, max_length=50)
    aggregation_group: Optional[str] = Field(None, max_length=50)
    verification_status: VerificationStatus = VerificationStatus.VERIFIED

class InterfaceCreate(InterfaceBase):
    pass

class InterfaceUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    interface_type: Optional[InterfaceType] = None
    mac_address: Optional[str] = None
    ip_address: Optional[str] = None
    subnet_mask: Optional[str] = None
    mode: Optional[InterfaceMode] = None
    access_vlan: Optional[int] = Field(None, ge=1, le=4094)
    allowed_vlans: Optional[str] = None
    speed_duplex: Optional[str] = None
    admin_status: Optional[str] = None
    operational_status: Optional[str] = None
    description: Optional[str] = None
    connected_equipment_id: Optional[str] = None
    connected_interface_name: Optional[str] = None
    link_type: Optional[str] = None
    aggregation_group: Optional[str] = None
    verification_status: Optional[VerificationStatus] = None

class InterfaceResponse(InterfaceBase):
    id: str
    equipment_id: str
    connected_equipment_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# -------------------------------------------------------------
# Network Segment (VLAN / Subnet) Schemas
# -------------------------------------------------------------
class NetworkSegmentBase(BaseModel):
    vlan_id: Optional[int] = Field(None, ge=1, le=4094)
    name: str = Field(..., min_length=2, max_length=150)
    cidr: Optional[str] = Field(None, max_length=50, description="Format CIDR ex. 192.168.1.0/24")
    gateway: Optional[str] = Field(None, max_length=50)
    dhcp_range: Optional[str] = Field(None, max_length=100)
    dns_servers: Optional[str] = Field(None, max_length=150)
    ntp_servers: Optional[str] = Field(None, max_length=150)
    zone: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    site_id: Optional[str] = None

class NetworkSegmentCreate(NetworkSegmentBase):
    pass

class NetworkSegmentUpdate(BaseModel):
    vlan_id: Optional[int] = Field(None, ge=1, le=4094)
    name: Optional[str] = Field(None, min_length=2, max_length=150)
    cidr: Optional[str] = None
    gateway: Optional[str] = None
    dhcp_range: Optional[str] = None
    dns_servers: Optional[str] = None
    ntp_servers: Optional[str] = None
    zone: Optional[str] = None
    description: Optional[str] = None
    site_id: Optional[str] = None

class NetworkSegmentResponse(NetworkSegmentBase):
    id: str
    project_id: str
    site_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# -------------------------------------------------------------
# Configuration Param Schemas
# -------------------------------------------------------------
class ConfigurationParamBase(BaseModel):
    category: str = Field(..., min_length=2, max_length=50) # network, routing, security, storage, etc.
    key: str = Field(..., min_length=2, max_length=100)
    value: str
    is_secret: bool = False
    description: Optional[str] = None
    data_source: str = "manual"
    equipment_id: Optional[str] = None
    verification_status: VerificationStatus = VerificationStatus.VERIFIED

class ConfigurationParamCreate(ConfigurationParamBase):
    pass

class ConfigurationParamUpdate(BaseModel):
    category: Optional[str] = Field(None, min_length=2, max_length=50)
    key: Optional[str] = Field(None, min_length=2, max_length=100)
    value: Optional[str] = None
    is_secret: Optional[bool] = None
    description: Optional[str] = None
    equipment_id: Optional[str] = None
    verification_status: Optional[VerificationStatus] = None

class ConfigurationParamResponse(ConfigurationParamBase):
    id: str
    project_id: str
    equipment_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
