"""API routes for downloading individual generated certificates."""

import os
import re
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Certificate, CertificateStatus

router = APIRouter(prefix="/certificates", tags=["Certificates"])


def _sanitize_filename(name: str) -> str:
    """Sanitize strings for safe attachment file naming."""
    cleaned = re.sub(r'[^\w\s-]', '', name).strip()
    return re.sub(r'[-\s]+', '_', cleaned) or "recipient"


@router.get(
    "/{certificate_id}/download",
    response_class=FileResponse,
    summary="Download Individual Certificate PDF",
    description="Downloads the generated PDF file for a specific certificate ID.",
)
def download_certificate(
    certificate_id: str,
    db: Session = Depends(get_db),
) -> FileResponse:
    """Return the generated PDF file for a certificate."""
    cert = db.query(Certificate).filter(Certificate.id == certificate_id).first()
    if not cert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Certificate with ID '{certificate_id}' not found.",
        )

    if cert.status != CertificateStatus.SUCCESS.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Certificate '{certificate_id}' is not ready for download. "
                f"Current status: '{cert.status}'. Error: {cert.error_message or 'None'}"
            ),
        )

    if not cert.file_path or not os.path.isfile(cert.file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Certificate PDF file is missing from disk storage.",
        )

    safe_name = _sanitize_filename(cert.recipient_name or "certificate")
    download_filename = f"certificate_{safe_name}_{cert.id[:8]}.pdf"

    return FileResponse(
        path=cert.file_path,
        media_type="application/pdf",
        filename=download_filename,
    )
