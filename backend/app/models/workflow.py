import enum
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base


class WorkflowAction(str, enum.Enum):
    SUBMIT = "submit"
    TECH_APPROVE = "tech_approve"
    TECH_REJECT = "tech_reject"
    FINAL_APPROVE = "final_approve"
    FINAL_REJECT = "final_reject"
    BRANCH_VERSION = "branch_version"
    RESET_DRAFT = "reset_draft"


class WorkflowDecision(Base):
    """
    Audit log of project lifecycle decisions and validation sign-offs.
    Conforms to MASTER_PROMPT Section 6.14:
    - soumission ingénieur
    - revue technique
    - validation finale
    - retour pour correction avec motif obligatoire
    - historisation complète avec horodatage UTC et utilisateur nominatif
    """
    __tablename__ = "workflow_decisions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    action = Column(String(50), nullable=False)
    from_status = Column(String(50), nullable=False)
    to_status = Column(String(50), nullable=False)
    version = Column(String(20), nullable=False, default="1.0")
    comment = Column(Text, nullable=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True
    )

    # Relationships
    project = relationship("Project", back_populates="decisions")
    user = relationship("User")

    def __repr__(self) -> str:
        return f"<WorkflowDecision {self.action} ({self.from_status} -> {self.to_status}) project={self.project_id}>"
