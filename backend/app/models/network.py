import enum
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Text, Boolean, DateTime, Enum, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.equipment import VerificationStatus

class InterfaceType(str, enum.Enum):
    PHYSICAL = "physical"
    VLAN_INTERFACE = "vlan_interface"  # SVI / Interface VLAN
    PORT_CHANNEL = "port_channel"      # LAG / EtherChannel / LACP
    LOOPBACK = "loopback"
    SUBINTERFACE = "subinterface"      # ex. Gi0/0.10
    MANAGEMENT = "management"
    TUNNEL = "tunnel"                  # GRE / VPN tunnel

class InterfaceMode(str, enum.Enum):
    ACCESS = "access"
    TRUNK = "trunk"
    ROUTED = "routed"
    UNCONFIGURED = "unconfigured"

class Interface(Base):
    __tablename__ = "interfaces"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    equipment_id = Column(String(36), ForeignKey("equipment.id", ondelete="CASCADE"), nullable=False, index=True)

    name = Column(String(100), nullable=False, index=True) # ex. "GigabitEthernet1/0/1", "eth0"
    interface_type = Column(Enum(InterfaceType), nullable=False, default=InterfaceType.PHYSICAL)
    mac_address = Column(String(50), nullable=True)
    ip_address = Column(String(50), nullable=True, index=True)
    subnet_mask = Column(String(50), nullable=True)
    mode = Column(Enum(InterfaceMode), nullable=False, default=InterfaceMode.ACCESS)
    access_vlan = Column(Integer, nullable=True)           # 1-4094
    allowed_vlans = Column(String(255), nullable=True)     # ex. "10,20,30-40"
    speed_duplex = Column(String(50), nullable=True)       # ex. "1000/Full", "10Gbps"
    admin_status = Column(String(20), nullable=False, default="up") # "up" / "down"
    operational_status = Column(String(20), nullable=True) # "up" / "down"
    description = Column(String(255), nullable=True)

    # Remote Connection (Equipment & Interface)
    connected_equipment_id = Column(String(36), ForeignKey("equipment.id", ondelete="SET NULL"), nullable=True, index=True)
    connected_interface_name = Column(String(100), nullable=True)
    link_type = Column(String(50), nullable=True)          # ex. "Fibre OM4", "Cuivre Cat6A", "Direct Attach"
    aggregation_group = Column(String(50), nullable=True)  # ex. "Po1", "bond0"

    verification_status = Column(
        Enum(VerificationStatus),
        nullable=False,
        default=VerificationStatus.VERIFIED
    )

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
    equipment = relationship("Equipment", foreign_keys=[equipment_id], back_populates="interfaces")
    connected_equipment = relationship("Equipment", foreign_keys=[connected_equipment_id])

    def __repr__(self) -> str:
        return f"<Interface {self.name} (Equipment: {self.equipment_id})>"


class NetworkSegment(Base):
    """
    Plan d'adressage IP et segmentation VLAN.
    """
    __tablename__ = "network_segments"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    site_id = Column(String(36), ForeignKey("sites.id", ondelete="SET NULL"), nullable=True, index=True)

    vlan_id = Column(Integer, nullable=True, index=True)    # 1-4094
    name = Column(String(150), nullable=False, index=True)  # ex. "VLAN-SERVEURS-PROD"
    cidr = Column(String(50), nullable=True, index=True)    # ex. "10.10.20.0/24"
    gateway = Column(String(50), nullable=True)             # ex. "10.10.20.254"
    dhcp_range = Column(String(100), nullable=True)         # ex. "10.10.20.50 - 10.10.20.200"
    dns_servers = Column(String(150), nullable=True)        # ex. "10.10.10.1, 10.10.10.2"
    ntp_servers = Column(String(150), nullable=True)
    zone = Column(String(100), nullable=True, index=True)   # ex. "LAN", "DMZ", "WAN", "Production"
    description = Column(Text, nullable=True)

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
    project = relationship("Project", backref="segments")
    site = relationship("Site", backref="segments")

    def __repr__(self) -> str:
        return f"<NetworkSegment VLAN {self.vlan_id} - {self.name} ({self.cidr})>"


class ConfigurationParam(Base):
    """
    Paramètres de configuration technique structurés par catégorie et équipement.
    """
    __tablename__ = "configurations"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    equipment_id = Column(String(36), ForeignKey("equipment.id", ondelete="CASCADE"), nullable=True, index=True)

    category = Column(String(50), nullable=False, index=True) # network, routing, security, storage, virtualization, backup, services
    key = Column(String(100), nullable=False, index=True)     # ex. "default_gateway", "syslog_server"
    value = Column(Text, nullable=False)
    is_secret = Column(Boolean, default=False, nullable=False) # true if secret/password
    description = Column(Text, nullable=True)
    data_source = Column(String(50), default="manual", nullable=False)

    verification_status = Column(
        Enum(VerificationStatus),
        nullable=False,
        default=VerificationStatus.VERIFIED
    )

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
    project = relationship("Project", backref="configurations")
    equipment = relationship("Equipment", back_populates="configurations")

    def __repr__(self) -> str:
        return f"<ConfigParam [{self.category}] {self.key}>"
