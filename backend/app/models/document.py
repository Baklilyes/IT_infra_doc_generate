"""Database model for generated documents (HLD, LLD, Annexes, Commissioning)."""
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from app.core.database import Base


class Document(Base):
    """Generated architecture deliverables in DOCX or PDF format."""
    __tablename__ = "documents"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    generated_by_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    document_type = Column(String(50), nullable=False, index=True)  # 'hld', 'lld', 'config_annexes', 'commissioning'
    title = Column(String(255), nullable=False)
    version = Column(String(20), default="1.0", nullable=False)
    file_format = Column(String(10), nullable=False)  # 'docx', 'pdf'
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer, default=0, nullable=False)

    ai_enhanced = Column(Boolean, default=False, nullable=False)
    is_locked = Column(Boolean, default=False, nullable=False)  # Locked when finalized in Lot 8

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    project = relationship("Project")
    generated_by = relationship("User")

    def __repr__(self) -> str:
        return f"<Document {self.id} - {self.document_type.upper()} ({self.file_format})>"
