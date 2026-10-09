"""Tests for per-item fault tolerance and error resilience."""

from unittest.mock import patch
from fastapi.testclient import TestClient
from app.services.certificate_generator import generate_certificate_pdf as original_generator


def test_generator_mock_failure_does_not_block_other_recipients(client: TestClient):
    """Verify that an unexpected crash in PDF generation for one recipient

    does not interrupt or fail the other recipients in the same job batch.
    """
    payload = {
        "recipients": [
            {
                "name": "Successful Recipient 1",
                "email": "user1@example.com",
                "course": "Distributed Systems",
                "date": "2026-10-09",
            },
            {
                "name": "Crash Candidate",
                "email": "user2@example.com",
                "course": "Distributed Systems",
                "date": "2026-10-09",
            },
            {
                "name": "Successful Recipient 3",
                "email": "user3@example.com",
                "course": "Distributed Systems",
                "date": "2026-10-09",
            },
        ]
    }

    def mock_generate(certificate_id, recipient_name, course_name, issue_date, extra_fields=None, output_dir=None):
        if recipient_name == "Crash Candidate":
            raise RuntimeError("Simulated ReportLab internal rendering crash!")
        return original_generator(
            certificate_id=certificate_id,
            recipient_name=recipient_name,
            course_name=course_name,
            issue_date=issue_date,
            extra_fields=extra_fields,
            output_dir=output_dir,
        )

    with patch("app.services.job_processor.generate_certificate_pdf", side_effect=mock_generate):
        resp = client.post("/api/jobs", json=payload)
        assert resp.status_code == 202
        job_id = resp.json()["job_id"]

    # Verify Job status
    status_resp = client.get(f"/api/jobs/{job_id}")
    assert status_resp.status_code == 200
    job_status = status_resp.json()
    assert job_status["status"] == "COMPLETED_WITH_ERRORS"
    assert job_status["total"] == 3
    assert job_status["success_count"] == 2
    assert job_status["failed_count"] == 1
    assert job_status["progress_percentage"] == 100.0

    # Verify individual certificate items
    certs_resp = client.get(f"/api/jobs/{job_id}/certificates")
    assert certs_resp.status_code == 200
    certs = certs_resp.json()["certificates"]

    cert1 = next(c for c in certs if c["recipient_name"] == "Successful Recipient 1")
    cert2 = next(c for c in certs if c["recipient_name"] == "Crash Candidate")
    cert3 = next(c for c in certs if c["recipient_name"] == "Successful Recipient 3")

    # Item 1 succeeded
    assert cert1["status"] == "SUCCESS"
    assert cert1["download_url"] is not None

    # Item 2 failed with exact error recorded
    assert cert2["status"] == "FAILED"
    assert "Simulated ReportLab internal rendering crash!" in cert2["error_message"]
    assert cert2["download_url"] is None

    # Item 3 succeeded despite item 2's failure
    assert cert3["status"] == "SUCCESS"
    assert cert3["download_url"] is not None


def test_all_recipients_fail_marks_job_failed(client: TestClient):
    """Verify that when all recipients fail, the job status is marked FAILED."""
    payload = {
        "recipients": [
            {
                "name": "Invalid One",
                "email": "not-valid-email-1",
                "course": "DevOps",
                "date": "2026-10-09",
            },
            {
                "name": "Invalid Two",
                "email": "not-valid-email-2",
                "course": "DevOps",
                "date": "2026-10-09",
            },
        ]
    }

    resp = client.post("/api/jobs", json=payload)
    assert resp.status_code == 202
    job_id = resp.json()["job_id"]

    status_resp = client.get(f"/api/jobs/{job_id}")
    assert status_resp.status_code == 200
    job_status = status_resp.json()
    assert job_status["status"] == "FAILED"
    assert job_status["success_count"] == 0
    assert job_status["failed_count"] == 2
