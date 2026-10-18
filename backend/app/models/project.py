import enum
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, Boolean, DateTime, Enum, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base

class ProjectStatus(str, enum.Enum):
    DRAFT = "draft"                     # Brouillon
    IN_PREPARATION = "in_preparation"   # En préparation
    IN_REVIEW = "in_review"             # En validation
    VALIDATED = "validated"             # Validé
    CLOSED = "closed"                   # Clôturé

class DocumentLanguage(str, enum.Enum):
    FR = "fr"
    EN = "en"

class Project(Base):
    __tablename__ = "projects"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    reference = Column(String(50), unique=True, index=True, nullable=False)
    name = Column(String(150), nullable=False, index=True)
    client_name = Column(String(150), nullable=False, index=True)
    description = Column(Text, nullable=True)
    scope = Column(Text, nullable=True)
    lead_name = Column(String(100), nullable=False)
    contributors = Column(Text, nullable=True)  # Comma-separated or descriptive text
    
    status = Column(
        Enum(ProjectStatus),
        nullable=False,
        default=ProjectStatus.DRAFT,
        index=True
    )
    document_language = Column(
        Enum(DocumentLanguage),
        nullable=False,
        default=DocumentLanguage.FR
    )
    target_date = Column(DateTime(timezone=True), nullable=True)
    is_archived = Column(Boolean, default=False, nullable=False, index=True)

    created_by_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
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
    created_by = relationship("User", foreign_keys=[created_by_id])
    sites = relationship("Site", back_populates="project", cascade="all, delete-orphan", order_by="Site.name")
    import_jobs = relationship("ImportJob", back_populates="project", cascade="all, delete-orphan", order_by="ImportJob.created_at.desc()")

    def __repr__(self) -> str:
        return f"<Project {self.reference} - {self.name} ({self.status.value})>"


class Site(Base):
    __tablename__ = "sites"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    
    name = Column(String(150), nullable=False, index=True)
    code = Column(String(50), nullable=True, index=True)  # e.g., "SITE-PARIS-01"
    address = Column(String(255), nullable=True)
    city = Column(String(100), nullable=True)
    country = Column(String(100), nullable=True, default="France")
    notes = Column(Text, nullable=True)

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
    project = relationship("Project", back_populates="sites")
    locations = relationship("Location", back_populates="site", cascade="all, delete-orphan", order_by="Location.name")

    def __repr__(self) -> str:
        return f"<Site {self.name} (Project: {self.project_id})>"


class Location(Base):
    """
    Salles techniques, baies et emplacements associés aux équipements sur un site.
    """
    __tablename__ = "locations"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    site_id = Column(String(36), ForeignKey("sites.id", ondelete="CASCADE"), nullable=False, index=True)

    name = Column(String(150), nullable=False)   # e.g., "Salle Serveurs Principal - Baie B01"
    room = Column(String(100), nullable=True)   # e.g., "Salle A102"
    rack = Column(String(50), nullable=True)    # e.g., "Rack 42U #1"
    notes = Column(Text, nullable=True)

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
    site = relationship("Site", back_populates="locations")

    def __repr__(self) -> str:
        return f"<Location {self.name} (Site: {self.site_id})>"
