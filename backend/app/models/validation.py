"""Database models for consistency validation runs, findings, and formal overrides."""
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, JSON, Text, Boolean
from sqlalchemy.orm import relationship
from app.core.database import Base


class ConsistencyReport(Base):
    """Execution history of deterministic consistency checks on a project."""
    __tablename__ = "consistency_reports"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    executed_by_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    status = Column(String(50), nullable=False, default="passed")  # 'passed', 'warnings_only', 'failed'
    blocking_count = Column(Integer, default=0, nullable=False)
    warning_count = Column(Integer, default=0, nullable=False)
    info_count = Column(Integer, default=0, nullable=False)
    resolved_count = Column(Integer, default=0, nullable=False)

    findings = Column(JSON, nullable=True)  # List of findings serialized as JSON
    summary = Column(Text, nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    project = relationship("Project")
    executed_by = relationship("User")

    def __repr__(self) -> str:
        return f"<ConsistencyReport {self.id} (Project {self.project_id} - Status: {self.status})>"


class ConsistencyOverride(Base):
    """
    Formal, audited justification (dérogation) to waive an anomaly rule finding.
    Section 8.3 & 6.8: Tout override d'un avertissement ou d'une anomalie
    doit comporter un motif horodaté et nominatif.
    """
    __tablename__ = "consistency_overrides"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    overridden_by_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    rule_code = Column(String(100), nullable=False, index=True)
    target_id = Column(String(100), nullable=False, index=True) # ID or key of target element
    target_type = Column(String(50), nullable=False)            # 'equipment', 'interface', 'segment', 'configuration'
    severity = Column(String(20), nullable=False)               # 'blocking', 'warning'
    
    justification = Column(Text, nullable=False)                # Mandatory explanation
    is_active = Column(Boolean, default=True, nullable=False)

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    project = relationship("Project")
    overridden_by = relationship("User")

    def __repr__(self) -> str:
        return f"<ConsistencyOverride {self.rule_code} on {self.target_type}:{self.target_id}>"
