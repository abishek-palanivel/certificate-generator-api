"""Direct unit tests for certificate generator and recipient validator functions."""

from pathlib import Path
import pytest
from app.services.certificate_generator import generate_certificate_pdf
from app.services.job_processor import RecipientValidationError, validate_recipient_data


def test_generate_certificate_pdf_creates_file(tmp_path: Path):
    """Test generating a certificate file directly to disk."""
    pdf_path = generate_certificate_pdf(
        certificate_id="test-cert-12345",
        recipient_name="Grace Brewster Murray Hopper",
        course_name="Introduction to Compilers",
        issue_date="2026-10-09",
        extra_fields={"grade": "A+", "honors": "Summa Cum Laude"},
        output_dir=tmp_path,
    )

    path = Path(pdf_path)
    assert path.exists()
    assert path.is_file()
    assert path.stat().st_size > 0
    with open(path, "rb") as f:
        header = f.read(4)
        assert header == b"%PDF"


def test_generate_certificate_pdf_empty_args_raises_value_error(tmp_path: Path):
    """Test that missing mandatory fields in the generator raise ValueError."""
    with pytest.raises(ValueError, match="certificate_id is required"):
        generate_certificate_pdf("", "Name", "Course", "2026-10-09", output_dir=tmp_path)

    with pytest.raises(ValueError, match="recipient_name cannot be empty"):
        generate_certificate_pdf("cert-1", "", "Course", "2026-10-09", output_dir=tmp_path)

    with pytest.raises(ValueError, match="course_name cannot be empty"):
        generate_certificate_pdf("cert-1", "Name", "", "2026-10-09", output_dir=tmp_path)

    with pytest.raises(ValueError, match="issue_date cannot be empty"):
        generate_certificate_pdf("cert-1", "Name", "Course", "", output_dir=tmp_path)


def test_validate_recipient_data_valid():
    """Test validator accepts valid recipient attributes."""
    # Should not raise
    validate_recipient_data(
        name="Valid User",
        email="user@domain.com",
        course_name="Machine Learning",
        issue_date="2026-10-09",
    )


def test_validate_recipient_data_errors():
    """Test validator flags missing or invalid values."""
    with pytest.raises(RecipientValidationError, match="Recipient name is required"):
        validate_recipient_data("", "user@example.com", "Course", "2026-10-09")

    with pytest.raises(RecipientValidationError, match="Recipient email is required"):
        validate_recipient_data("Name", "", "Course", "2026-10-09")

    with pytest.raises(RecipientValidationError, match="Invalid email address format"):
        validate_recipient_data("Name", "plainaddress", "Course", "2026-10-09")

    with pytest.raises(RecipientValidationError, match="Course/event name is required"):
        validate_recipient_data("Name", "user@example.com", "", "2026-10-09")

    with pytest.raises(RecipientValidationError, match="Issue date is required"):
        validate_recipient_data("Name", "user@example.com", "Course", "")
