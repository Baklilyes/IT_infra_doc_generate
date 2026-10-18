import enum
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, DateTime, Enum, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.core.database import Base

class EquipmentCategory(str, enum.Enum):
    SWITCH = "switch"
    ROUTER = "router"
    FIREWALL = "firewall"
    PHYSICAL_SERVER = "physical_server"
    HYPERVISOR = "hypervisor"
    VIRTUAL_MACHINE = "virtual_machine"
    STORAGE = "storage"
    WIFI = "wifi"
    GENERIC = "generic"

class InstallationStatus(str, enum.Enum):
    PLANNED = "planned"                 # Planifié
    INSTALLED = "installed"             # Installé
    IN_SERVICE = "in_service"           # En service
    DECOMMISSIONED = "decommissioned"   # Démantelé

class VerificationStatus(str, enum.Enum):
    UNVERIFIED = "unverified"           # À vérifier
    AI_PROPOSED = "ai_proposed"         # Proposé par IA
    VERIFIED = "verified"               # Vérifié par un utilisateur

class Equipment(Base):
    __tablename__ = "equipment"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    site_id = Column(String(36), ForeignKey("sites.id", ondelete="SET NULL"), nullable=True, index=True)
    location_id = Column(String(36), ForeignKey("locations.id", ondelete="SET NULL"), nullable=True, index=True)

    name = Column(String(150), nullable=False, index=True)           # Hostname ou libellé
    category = Column(Enum(EquipmentCategory), nullable=False, index=True)
    subcategory = Column(String(100), nullable=True)                 # ex. "Core Switch", "Edge Firewall"
    manufacturer = Column(String(100), nullable=True, index=True)    # ex. "Cisco", "Dell", "Fortinet"
    model = Column(String(100), nullable=True, index=True)           # ex. "Catalyst 9300", "FortiGate 100F"
    serial_number = Column(String(100), nullable=True, index=True)
    management_ip = Column(String(50), nullable=True, index=True)
    firmware_version = Column(String(100), nullable=True)            # Version logicielle ou firmware
    role = Column(String(150), nullable=True)                        # Usage fonctionnel

    installation_status = Column(
        Enum(InstallationStatus),
        nullable=False,
        default=InstallationStatus.IN_SERVICE,
        index=True
    )
    verification_status = Column(
        Enum(VerificationStatus),
        nullable=False,
        default=VerificationStatus.VERIFIED,
        index=True
    )
    data_source = Column(String(50), default="manual", nullable=False) # manual, csv_import, xlsx_import, cli_config
    notes = Column(Text, nullable=True)

    # Specific category attributes (RAM/CPU for servers, HA for firewalls, PoE for switches, RAID for SAN/NAS)
    specific_attributes = Column(JSON, nullable=True, default=dict)

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    project = relationship("Project", backref="equipment")
    site = relationship("Site", backref="equipment")
    location = relationship("Location", backref="equipment")
    interfaces = relationship(
        "Interface",
        back_populates="equipment",
        foreign_keys="Interface.equipment_id",
        cascade="all, delete-orphan",
        order_by="Interface.name"
    )
    configurations = relationship(
        "ConfigurationParam",
        back_populates="equipment",
        cascade="all, delete-orphan",
        order_by="ConfigurationParam.category, ConfigurationParam.key"
    )

    def __repr__(self) -> str:
        return f"<Equipment {self.name} ({self.category.value} - {self.model})>"
