"""Import Job models for tracking data ingestion and findings."""
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, JSON, Text
from sqlalchemy.orm import relationship
from app.core.database import Base


class ImportJob(Base):
    __tablename__ = "import_jobs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    filename = Column(String(255), nullable=False)
    file_type = Column(String(50), nullable=False)  # 'csv', 'excel', 'cisco_ios', 'fortinet_cli', 'json'
    target_type = Column(String(50), default="equipment")  # 'equipment', 'network_segments', 'mixed'
    status = Column(String(50), default="pending")  # 'pending', 'previewed', 'applied', 'failed'
    
    total_rows = Column(Integer, default=0)
    created_count = Column(Integer, default=0)
    updated_count = Column(Integer, default=0)
    skipped_count = Column(Integer, default=0)
    error_count = Column(Integer, default=0)

    mappings = Column(JSON, nullable=True)
    preview_data = Column(JSON, nullable=True)
    raw_content = Column(Text, nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    applied_at = Column(
        DateTime(timezone=True),
        nullable=True
    )

    # Relationships
    project = relationship("Project", back_populates="import_jobs")
    user = relationship("User")

    def __repr__(self) -> str:
        return f"<ImportJob {self.id} - {self.filename} ({self.status})>"
