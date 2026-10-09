"""API routes for managing bulk certificate generation jobs."""

import io
import os
import re
import zipfile
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Certificate, CertificateStatus, Job, JobStatus
from app.schemas import (
    CertificateItemResponse,
    CreateJobRequest,
    JobCertificatesResponse,
    JobCreatedResponse,
    JobStatusResponse,
)
from app.services.job_processor import process_job

router = APIRouter(prefix="/jobs", tags=["Jobs"])


def _sanitize_filename(name: str) -> str:
    """Sanitize strings for safe file naming in zip archives."""
    cleaned = re.sub(r'[^\w\s-]', '', name).strip()
    return re.sub(r'[-\s]+', '_', cleaned) or "recipient"


@router.post(
    "",
    response_model=JobCreatedResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Create Bulk Certificate Generation Job",
    description="Submits a list of recipients to generate certificates in the background.",
)
def create_job(
    payload: CreateJobRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> JobCreatedResponse:
    """Accept and enqueue a bulk certificate generation job."""
    # 1. Create parent Job record
    new_job = Job(
        status=JobStatus.PENDING.value,
        total_recipients=len(payload.recipients),
        success_count=0,
        failed_count=0,
    )
    db.add(new_job)
    db.flush()  # Populate new_job.id before certificate creation

    # 2. Create pending Certificate records for all recipients
    for recipient in payload.recipients:
        cert = Certificate(
            job_id=new_job.id,
            recipient_name=recipient.name,
            recipient_email=recipient.email,
            course_name=recipient.course_name,
            issue_date=recipient.issue_date,
            extra_fields=recipient.extra_fields,
            status=CertificateStatus.PENDING.value,
        )
        db.add(cert)

    db.commit()
    db.refresh(new_job)

    # 3. Schedule asynchronous background processing
    background_tasks.add_task(process_job, new_job.id)

    return JobCreatedResponse(
        job_id=new_job.id,
        status=new_job.status,
        total_recipients=new_job.total_recipients,
        created_at=new_job.created_at,
        message="Job accepted and queued for background processing.",
    )


@router.get(
    "/{job_id}",
    response_model=JobStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Job Status and Progress",
    description="Retrieve the current execution status, item counts, and progress percentage for a job.",
)
def get_job_status(job_id: str, db: Session = Depends(get_db)) -> JobStatusResponse:
    """Retrieve execution metrics and status for a specific job."""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job with ID '{job_id}' not found.",
        )

    return JobStatusResponse(
        job_id=job.id,
        status=job.status,
        total=job.total_recipients,
        success_count=job.success_count,
        failed_count=job.failed_count,
        progress_percentage=job.progress_percentage,
        error_message=job.error_message,
        created_at=job.created_at,
        updated_at=job.updated_at,
    )


@router.get(
    "/{job_id}/certificates",
    response_model=JobCertificatesResponse,
    status_code=status.HTTP_200_OK,
    summary="List Certificates for Job",
    description="Retrieve all certificate records, individual statuses, errors, and download links.",
)
def get_job_certificates(job_id: str, db: Session = Depends(get_db)) -> JobCertificatesResponse:
    """List all individual certificates and their statuses for a given job."""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job with ID '{job_id}' not found.",
        )

    certificates = (
        db.query(Certificate)
        .filter(Certificate.job_id == job_id)
        .order_by(Certificate.created_at)
        .all()
    )

    items: list[CertificateItemResponse] = []
    for cert in certificates:
        download_url = None
        if cert.status == CertificateStatus.SUCCESS.value:
            download_url = f"/api/certificates/{cert.id}/download"

        items.append(
            CertificateItemResponse(
                certificate_id=cert.id,
                recipient_name=cert.recipient_name,
                recipient_email=cert.recipient_email,
                course_name=cert.course_name,
                issue_date=cert.issue_date,
                status=cert.status,
                error_message=cert.error_message,
                download_url=download_url,
                created_at=cert.created_at,
            )
        )

    return JobCertificatesResponse(
        job_id=job.id,
        total=len(items),
        certificates=items,
    )


@router.get(
    "/{job_id}/download",
    status_code=status.HTTP_200_OK,
    summary="Download All Successful Certificates as ZIP",
    description="Bundles all successfully generated PDF certificates for a job into a single ZIP archive.",
)
def download_job_certificates_zip(job_id: str, db: Session = Depends(get_db)) -> Response:
    """Create and return a ZIP archive containing all successful PDFs for the job."""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job with ID '{job_id}' not found.",
        )

    successful_certs = (
        db.query(Certificate)
        .filter(
            Certificate.job_id == job_id,
            Certificate.status == CertificateStatus.SUCCESS.value,
        )
        .all()
    )

    if not successful_certs:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No successful certificates available for download for this job.",
        )

    # Build ZIP archive in memory
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        added_files = 0
        for cert in successful_certs:
            if cert.file_path and os.path.exists(cert.file_path):
                safe_name = _sanitize_filename(cert.recipient_name or "recipient")
                zip_filename = f"certificate_{safe_name}_{cert.id[:8]}.pdf"
                zf.write(cert.file_path, arcname=zip_filename)
                added_files += 1

    if added_files == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Generated certificate files could not be located on disk.",
        )

    zip_buffer.seek(0)
    archive_filename = f"certificates_job_{job_id[:8]}.zip"

    return Response(
        content=zip_buffer.getvalue(),
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{archive_filename}"',
        },
    )
