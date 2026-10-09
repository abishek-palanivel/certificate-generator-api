"""Tests for job submission, validation, progress tracking, and certificates listing."""

from fastapi.testclient import TestClient


def test_create_generation_job_success(client: TestClient):
    """Test successful creation and synchronous test execution of a bulk generation job."""
    payload = {
        "recipients": [
            {
                "name": "Alan Turing",
                "email": "alan.turing@example.com",
                "course": "Theoretical Computer Science",
                "date": "2026-10-09",
                "extra_fields": {"grade": "A+", "honor": "Distinction"},
            },
            {
                "name": "Ada Lovelace",
                "email": "ada.lovelace@example.com",
                "course": "Analytical Engine Programming",
                "date": "2026-10-09",
            },
        ]
    }

    response = client.post("/api/jobs", json=payload)
    assert response.status_code == 202
    data = response.json()
    assert "job_id" in data
    assert data["total_recipients"] == 2
    assert data["message"] == "Job accepted and queued for background processing."

    job_id = data["job_id"]

    # In TestClient, BackgroundTasks run during request handling.
    # Verify final status through status endpoint:
    status_resp = client.get(f"/api/jobs/{job_id}")
    assert status_resp.status_code == 200
    status_data = status_resp.json()
    assert status_data["job_id"] == job_id
    assert status_data["status"] == "COMPLETED"
    assert status_data["total"] == 2
    assert status_data["success_count"] == 2
    assert status_data["failed_count"] == 0
    assert status_data["progress_percentage"] == 100.0


def test_input_validation_empty_recipient_list(client: TestClient):
    """Test that submitting an empty recipients list returns 422 Unprocessable Entity."""
    response = client.post("/api/jobs", json={"recipients": []})
    assert response.status_code == 422
    assert "Recipients list cannot be empty" in str(response.json())


def test_input_validation_exceeds_max_recipients(client: TestClient, monkeypatch):
    """Test that submitting more than the maximum allowed recipients triggers validation error."""
    from app.config import settings
    monkeypatch.setattr(settings, "MAX_RECIPIENTS_PER_JOB", 3)

    payload = {
        "recipients": [
            {"name": f"User {i}", "email": f"user{i}@example.com", "course": "Python", "date": "2026-10-09"}
            for i in range(4)
        ]
    }
    response = client.post("/api/jobs", json=payload)
    assert response.status_code == 422
    assert "exceeds maximum allowed limit" in str(response.json())


def test_input_validation_bad_email_and_missing_name_non_blocking(client: TestClient):
    """Test that individual bad recipients fail with clear messages without blocking valid ones."""
    payload = {
        "recipients": [
            # 1. Valid recipient
            {
                "name": "Grace Hopper",
                "email": "grace.hopper@navy.mil",
                "course": "Compiler Design",
                "date": "2026-10-09",
            },
            # 2. Recipient with bad email
            {
                "name": "Invalid Email Person",
                "email": "not-an-email-address",
                "course": "Compiler Design",
                "date": "2026-10-09",
            },
            # 3. Recipient with missing / empty name
            {
                "name": "   ",
                "email": "missing.name@example.com",
                "course": "Compiler Design",
                "date": "2026-10-09",
            },
        ]
    }

    response = client.post("/api/jobs", json=payload)
    assert response.status_code == 202
    job_id = response.json()["job_id"]

    # Check job status: 1 success + 2 failed => COMPLETED_WITH_ERRORS
    status_resp = client.get(f"/api/jobs/{job_id}")
    assert status_resp.status_code == 200
    status_data = status_resp.json()
    assert status_data["status"] == "COMPLETED_WITH_ERRORS"
    assert status_data["total"] == 3
    assert status_data["success_count"] == 1
    assert status_data["failed_count"] == 2
    assert status_data["progress_percentage"] == 100.0

    # Inspect individual certificates list
    certs_resp = client.get(f"/api/jobs/{job_id}/certificates")
    assert certs_resp.status_code == 200
    certs_data = certs_resp.json()
    assert certs_data["total"] == 3
    certs = certs_data["certificates"]

    # 1. Valid recipient should have SUCCESS and download_url
    grace_cert = next(c for c in certs if c["recipient_email"] == "grace.hopper@navy.mil")
    assert grace_cert["status"] == "SUCCESS"
    assert grace_cert["error_message"] is None
    assert grace_cert["download_url"] is not None
    assert f"/api/certificates/{grace_cert['certificate_id']}/download" in grace_cert["download_url"]

    # 2. Bad email recipient should have FAILED with descriptive error
    bad_email_cert = next(c for c in certs if c["recipient_name"] == "Invalid Email Person")
    assert bad_email_cert["status"] == "FAILED"
    assert "Invalid email address format" in bad_email_cert["error_message"]
    assert bad_email_cert["download_url"] is None

    # 3. Missing name recipient should have FAILED with descriptive error
    missing_name_cert = next(c for c in certs if c["recipient_email"] == "missing.name@example.com")
    assert missing_name_cert["status"] == "FAILED"
    assert "Recipient name is required and cannot be empty" in missing_name_cert["error_message"]
    assert missing_name_cert["download_url"] is None


def test_get_job_status_not_found(client: TestClient):
    """Test retrieving status of a non-existent job returns 404."""
    response = client.get("/api/jobs/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()
