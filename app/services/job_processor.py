"""Background job processing service for bulk certificate generation.

Handles recipient data validation, PDF rendering orchestration, per-item
fault tolerance, and real-time job status tracking.
"""

import logging
from datetime import datetime, timezone
from email_validator import EmailNotValidError, validate_email
from sqlalchemy.orm import Session

from app.config import settings
from app.database import SessionLocal
from app.models import Certificate, CertificateStatus, Job, JobStatus
from app.services.certificate_generator import generate_certificate_pdf

logger = logging.getLogger(__name__)


class RecipientValidationError(Exception):
    """Custom exception raised when recipient attributes fail validation checks."""
    pass


def validate_recipient_data(
    name: str | None,
    email: str | None,
    course_name: str | None,
    issue_date: str | None,
) -> None:
    """Validate required recipient fields according to business rules.

    Raises:
        RecipientValidationError: With an explicit reason if any validation fails.
    """
    # 1. Recipient Name validation
    if name is None or not name.strip():
        raise RecipientValidationError("Recipient name is required and cannot be empty.")
    if len(name.strip()) > settings.MAX_NAME_LENGTH:
        raise RecipientValidationError(
            f"Recipient name exceeds maximum allowed length of {settings.MAX_NAME_LENGTH} characters."
        )

    # 2. Recipient Email validation
    if email is None or not email.strip():
        raise RecipientValidationError("Recipient email is required and cannot be empty.")
    if len(email.strip()) > settings.MAX_EMAIL_LENGTH:
        raise RecipientValidationError(
            f"Recipient email exceeds maximum allowed length of {settings.MAX_EMAIL_LENGTH} characters."
        )
    try:
        validate_email(email.strip(), check_deliverability=False)
    except EmailNotValidError as exc:
        raise RecipientValidationError(f"Invalid email address format: '{email}'. {str(exc)}") from exc

    # 3. Course / Event Name validation
    if course_name is None or not course_name.strip():
        raise RecipientValidationError("Course/event name is required and cannot be empty.")
    if len(course_name.strip()) > settings.MAX_COURSE_LENGTH:
        raise RecipientValidationError(
            f"Course name exceeds maximum allowed length of {settings.MAX_COURSE_LENGTH} characters."
        )

    # 4. Issue Date validation
    if issue_date is None or not str(issue_date).strip():
        raise RecipientValidationError("Issue date is required and cannot be empty.")


def process_job(job_id: str, db_factory=None) -> None:
    """Process a bulk certificate generation job asynchronously.

    Executes isolated per-item generation so that failure on one recipient
    never halts or corrupts generation for other recipients.

    Args:
        job_id: Unique UUID string identifying the Job.
        db_factory: Optional SQLAlchemy sessionmaker callable.
    """
    factory = db_factory or SessionLocal
    db: Session = factory()
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            logger.error(f"Job {job_id} not found in database.")
            return

        # Mark job as currently processing
        job.status = JobStatus.PROCESSING.value
        job.updated_at = datetime.now(timezone.utc)
        db.commit()

        # Query all certificates scheduled for this job
        certificates = (
            db.query(Certificate)
            .filter(Certificate.job_id == job_id)
            .order_by(Certificate.created_at)
            .all()
        )

        for cert in certificates:
            try:
                # 1. Validate recipient details
                validate_recipient_data(
                    name=cert.recipient_name,
                    email=cert.recipient_email,
                    course_name=cert.course_name,
                    issue_date=cert.issue_date,
                )

                # 2. Generate PDF certificate
                pdf_path = generate_certificate_pdf(
                    certificate_id=cert.id,
                    recipient_name=cert.recipient_name or "",
                    course_name=cert.course_name or "",
                    issue_date=cert.issue_date or "",
                    extra_fields=cert.extra_fields,
                )

                # 3. Mark individual certificate as successful
                cert.status = CertificateStatus.SUCCESS.value
                cert.file_path = pdf_path
                cert.error_message = None
                job.success_count += 1

            except Exception as exc:
                # Per-item isolation: failure on one recipient records error without stopping others
                logger.warning(
                    f"Certificate generation failed for recipient {cert.recipient_email or cert.id}: {exc}"
                )
                cert.status = CertificateStatus.FAILED.value
                cert.error_message = str(exc)
                job.failed_count += 1

            finally:
                cert.updated_at = datetime.now(timezone.utc)
                job.updated_at = datetime.now(timezone.utc)
                db.commit()  # Incrementally commit progress

        # Determine final overall job status
        if job.failed_count == 0:
            job.status = JobStatus.COMPLETED.value
        elif job.success_count > 0:
            job.status = JobStatus.COMPLETED_WITH_ERRORS.value
        else:
            job.status = JobStatus.FAILED.value

        job.updated_at = datetime.now(timezone.utc)
        db.commit()
        logger.info(
            f"Job {job_id} completed with status {job.status} "
            f"({job.success_count} success, {job.failed_count} failed)"
        )

    except Exception as fatal_exc:
        logger.exception(f"Fatal error while processing job {job_id}: {fatal_exc}")
        db.rollback()
        try:
            job = db.query(Job).filter(Job.id == job_id).first()
            if job:
                job.status = JobStatus.FAILED.value
                job.error_message = f"Job processing aborted: {str(fatal_exc)}"
                job.updated_at = datetime.now(timezone.utc)
                db.commit()
        except Exception:
            logger.exception("Failed to update job status to FAILED after fatal error.")
    finally:
        db.close()
