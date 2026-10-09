"""SQLAlchemy database models and status enumerations."""

import enum
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from app.database import Base


def utc_now() -> datetime:
    """Return current UTC datetime."""
    return datetime.now(timezone.utc)


class JobStatus(str, enum.Enum):
    """Execution status for bulk certificate generation jobs."""
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    COMPLETED_WITH_ERRORS = "COMPLETED_WITH_ERRORS"
    FAILED = "FAILED"


class CertificateStatus(str, enum.Enum):
    """Processing status for individual recipient certificates."""
    PENDING = "PENDING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


class Job(Base):
    """Represents a bulk certificate generation job."""
    __tablename__ = "jobs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    status = Column(String(32), nullable=False, default=JobStatus.PENDING.value, index=True)
    total_recipients = Column(Integer, nullable=False, default=0)
    success_count = Column(Integer, nullable=False, default=0)
    failed_count = Column(Integer, nullable=False, default=0)
    error_message = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now)

    # Relationship to individual recipient certificates
    certificates = relationship(
        "Certificate",
        back_populates="job",
        cascade="all, delete-orphan",
        order_by="Certificate.created_at",
        lazy="selectin",
    )

    @property
    def progress_percentage(self) -> float:
        """Calculate progress percentage based on processed items."""
        if self.total_recipients <= 0:
            return 0.0
        processed = self.success_count + self.failed_count
        return round((processed / self.total_recipients) * 100.0, 2)


class Certificate(Base):
    """Represents an individual certificate generated for a recipient."""
    __tablename__ = "certificates"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    job_id = Column(String(36), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True)

    recipient_name = Column(String(255), nullable=True)
    recipient_email = Column(String(255), nullable=True)
    course_name = Column(String(255), nullable=True)
    issue_date = Column(String(64), nullable=True)
    extra_fields = Column(JSON, nullable=True)

    status = Column(String(32), nullable=False, default=CertificateStatus.PENDING.value, index=True)
    file_path = Column(String(500), nullable=True)
    error_message = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now)

    # Back-reference to the parent job
    job = relationship("Job", back_populates="certificates")
