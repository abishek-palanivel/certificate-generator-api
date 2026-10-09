"""Tests for certificate file generation, single PDF download, and bulk ZIP download."""

import io
import os
import zipfile
from fastapi.testclient import TestClient


def test_certificate_pdf_created_and_non_empty(client: TestClient):
    """Test that generated PDF exists on disk, is non-empty, and has valid PDF headers."""
    payload = {
        "recipients": [
            {
                "name": "Margaret Hamilton",
                "email": "margaret.hamilton@mit.edu",
                "course": "Apollo Flight Guidance Software",
                "date": "1969-07-20",
                "extra_fields": {"mission": "Apollo 11", "role": "Lead Software Engineer"},
            }
        ]
    }

    resp = client.post("/api/jobs", json=payload)
    assert resp.status_code == 202
    job_id = resp.json()["job_id"]

    certs_resp = client.get(f"/api/jobs/{job_id}/certificates")
    assert certs_resp.status_code == 200
    cert = certs_resp.json()["certificates"][0]
    cert_id = cert["certificate_id"]
    assert cert["status"] == "SUCCESS"

    # Download certificate PDF directly
    download_resp = client.get(f"/api/certificates/{cert_id}/download")
    assert download_resp.status_code == 200
    assert download_resp.headers["content-type"] == "application/pdf"
    assert "attachment" in download_resp.headers["content-disposition"]

    # Validate that PDF content is non-empty and starts with standard PDF magic number
    pdf_bytes = download_resp.content
    assert len(pdf_bytes) > 1000  # ReportLab certificate is several kilobytes
    assert pdf_bytes.startswith(b"%PDF")


def test_download_job_certificates_zip(client: TestClient):
    """Test downloading all successful certificates in a job as a valid ZIP archive."""
    payload = {
        "recipients": [
            {
                "name": "Katherine Johnson",
                "email": "katherine.johnson@nasa.gov",
                "course": "Orbital Mechanics",
                "date": "2026-10-09",
            },
            {
                "name": "Dorothy Vaughan",
                "email": "dorothy.vaughan@nasa.gov",
                "course": "FORTRAN Programming",
                "date": "2026-10-09",
            },
        ]
    }

    create_resp = client.post("/api/jobs", json=payload)
    job_id = create_resp.json()["job_id"]

    # Request ZIP archive
    zip_resp = client.get(f"/api/jobs/{job_id}/download")
    assert zip_resp.status_code == 200
    assert zip_resp.headers["content-type"] == "application/zip"
    assert f"certificates_job_{job_id[:8]}.zip" in zip_resp.headers["content-disposition"]

    # Inspect zip contents in-memory
    zip_buffer = io.BytesIO(zip_resp.content)
    with zipfile.ZipFile(zip_buffer, mode="r") as zf:
        file_list = zf.namelist()
        assert len(file_list) == 2
        for filename in file_list:
            assert filename.endswith(".pdf")
            file_data = zf.read(filename)
            assert len(file_data) > 0
            assert file_data.startswith(b"%PDF")


def test_download_certificate_not_found(client: TestClient):
    """Test downloading a non-existent certificate returns 404."""
    resp = client.get("/api/certificates/00000000-0000-0000-0000-000000000000/download")
    assert resp.status_code == 404


def test_download_failed_certificate_returns_400(client: TestClient):
    """Test attempting to download a FAILED certificate returns 400 Bad Request."""
    payload = {
        "recipients": [
            {
                "name": "Invalid Recipient",
                "email": "invalid-email-syntax",
                "course": "Sample Course",
                "date": "2026-10-09",
            }
        ]
    }
    create_resp = client.post("/api/jobs", json=payload)
    job_id = create_resp.json()["job_id"]

    certs = client.get(f"/api/jobs/{job_id}/certificates").json()["certificates"]
    failed_id = certs[0]["certificate_id"]
    assert certs[0]["status"] == "FAILED"

    resp = client.get(f"/api/certificates/{failed_id}/download")
    assert resp.status_code == 400
    assert "not ready for download" in resp.json()["detail"].lower()


def test_download_job_zip_no_successful_certificates_returns_400(client: TestClient):
    """Test downloading ZIP for a job with no successful certificates returns 400."""
    payload = {
        "recipients": [
            {
                "name": "Invalid Recipient",
                "email": "not-valid-email",
                "course": "Sample Course",
                "date": "2026-10-09",
            }
        ]
    }
    create_resp = client.post("/api/jobs", json=payload)
    job_id = create_resp.json()["job_id"]

    resp = client.get(f"/api/jobs/{job_id}/download")
    assert resp.status_code == 400
    assert "no successful certificates" in resp.json()["detail"].lower()
