"""Pydantic request and response schemas with data validation."""

from datetime import datetime
from typing import Any
from pydantic import BaseModel, ConfigDict, Field, field_validator
from app.config import settings


class RecipientInput(BaseModel):
    """Schema for individual recipient input in a bulk generation job."""
    model_config = ConfigDict(populate_by_name=True)

    name: str | None = Field(default=None, description="Recipient full name")
    email: str | None = Field(default=None, description="Recipient email address")
    course_name: str | None = Field(
        default=None,
        alias="course",
        description="Name of the course, workshop, or event",
    )
    issue_date: str | None = Field(
        default=None,
        alias="date",
        description="Date of certificate issuance (e.g. 2026-10-09 or October 9, 2026)",
    )
    extra_fields: dict[str, Any] | None = Field(
        default=None,
        description="Optional metadata such as grade, instructor, or organization",
    )


class CreateJobRequest(BaseModel):
    """Request payload for creating a bulk certificate generation job."""
    recipients: list[RecipientInput] = Field(
        ...,
        description="List of recipients to generate certificates for",
    )

    @field_validator("recipients")
    @classmethod
    def validate_recipients_list(cls, v: list[RecipientInput]) -> list[RecipientInput]:
        """Validate recipient list size constraints."""
        if not v:
            raise ValueError("Recipients list cannot be empty. Please provide at least one recipient.")
        if len(v) > settings.MAX_RECIPIENTS_PER_JOB:
            raise ValueError(
                f"Recipients count ({len(v)}) exceeds maximum allowed limit of {settings.MAX_RECIPIENTS_PER_JOB}."
            )
        return v


class JobCreatedResponse(BaseModel):
    """202 Accepted response upon successfully enqueuing a generation job."""
    job_id: str
    status: str
    total_recipients: int
    created_at: datetime
    message: str = "Job accepted and queued for background processing."


class JobStatusResponse(BaseModel):
    """Detailed job status and progress response."""
    job_id: str
    status: str
    total: int
    success_count: int
    failed_count: int
    progress_percentage: float
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime


class CertificateItemResponse(BaseModel):
    """Details for a single generated or failed certificate."""
    certificate_id: str
    recipient_name: str | None = None
    recipient_email: str | None = None
    course_name: str | None = None
    issue_date: str | None = None
    status: str
    error_message: str | None = None
    download_url: str | None = None
    created_at: datetime


class JobCertificatesResponse(BaseModel):
    """List of all certificates associated with a job."""
    job_id: str
    total: int
    certificates: list[CertificateItemResponse]
