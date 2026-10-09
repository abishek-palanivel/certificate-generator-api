"""PDF Certificate Generation service using ReportLab.

Renders high-quality, professional landscape certificates of completion
with custom borders, typography, seal badges, and verified metadata.
"""

from pathlib import Path
from typing import Any
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import letter, landscape
from reportlab.pdfgen import canvas
from app.config import settings

# Predefined styling palette
COLOR_PRIMARY_NAVY = HexColor("#0F172A")    # Deep slate navy
COLOR_SECONDARY_GOLD = HexColor("#C5A059")  # Sophisticated warm gold
COLOR_DARK_TEXT = HexColor("#1E293B")       # Dark charcoal
COLOR_MUTED_TEXT = HexColor("#64748B")      # Muted slate gray
COLOR_LIGHT_ACCENT = HexColor("#E2E8F0")    # Divider light gray
COLOR_SEAL_BG = HexColor("#FEF9C3")         # Light gold tint


def generate_certificate_pdf(
    certificate_id: str,
    recipient_name: str,
    course_name: str,
    issue_date: str,
    extra_fields: dict[str, Any] | None = None,
    output_dir: Path | None = None,
) -> str:
    """Generate a single PDF certificate of completion.

    Args:
        certificate_id: Unique UUID string for the certificate.
        recipient_name: Full name of the recipient.
        course_name: Course, workshop, or event title.
        issue_date: String representation of the issuance date.
        extra_fields: Optional dictionary containing extra attributes (e.g. grade, issuer).
        output_dir: Directory where the PDF should be stored. Defaults to settings.STORAGE_DIR.

    Returns:
        The absolute file path to the generated PDF.

    Raises:
        ValueError: If mandatory parameters are missing or invalid.
        OSError: If writing to the file system fails.
    """
    if not certificate_id:
        raise ValueError("certificate_id is required to generate a certificate.")
    if not recipient_name or not recipient_name.strip():
        raise ValueError("recipient_name cannot be empty.")
    if not course_name or not course_name.strip():
        raise ValueError("course_name cannot be empty.")
    if not issue_date or not str(issue_date).strip():
        raise ValueError("issue_date cannot be empty.")

    target_dir = output_dir or settings.STORAGE_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = target_dir / f"{certificate_id}.pdf"

    # Dimensions for Letter Landscape: 792 x 612 pt
    page_width, page_height = landscape(letter)
    c = canvas.Canvas(str(pdf_path), pagesize=(page_width, page_height))
    c.setTitle(f"Certificate of Completion - {recipient_name}")
    c.setAuthor("Bulk Certificate Generator API")
    c.setSubject(course_name)

    center_x = page_width / 2.0

    # 1. Outer & Inner Decorative Borders
    # Outer Border (Navy, 3.5pt)
    c.setStrokeColor(COLOR_PRIMARY_NAVY)
    c.setLineWidth(3.5)
    c.rect(26, 26, page_width - 52, page_height - 52)

    # Inner Border (Gold, 1.2pt)
    c.setStrokeColor(COLOR_SECONDARY_GOLD)
    c.setLineWidth(1.2)
    c.rect(36, 36, page_width - 72, page_height - 72)

    # Corner Decorative Squares
    corner_size = 8
    c.setFillColor(COLOR_SECONDARY_GOLD)
    for cx, cy in [
        (36, 36),
        (page_width - 36 - corner_size, 36),
        (36, page_height - 36 - corner_size),
        (page_width - 36 - corner_size, page_height - 36 - corner_size),
    ]:
        c.rect(cx, cy, corner_size, corner_size, fill=1, stroke=0)

    # 2. Header Pre-title
    c.setFillColor(COLOR_MUTED_TEXT)
    c.setFont("Helvetica-Bold", 10)
    c.drawCentredString(center_x, 520, "OFFICIAL RECOGNITION & ACCREDITATION")

    # 3. Main Certificate Title
    c.setFillColor(COLOR_PRIMARY_NAVY)
    c.setFont("Helvetica-Bold", 32)
    c.drawCentredString(center_x, 470, "Certificate of Completion")

    # Ornamental divider under title
    c.setStrokeColor(COLOR_SECONDARY_GOLD)
    c.setLineWidth(1.5)
    c.line(center_x - 120, 452, center_x + 120, 452)
    c.setFillColor(COLOR_SECONDARY_GOLD)
    c.circle(center_x, 452, 3, fill=1, stroke=0)

    # 4. Presentation line
    c.setFillColor(COLOR_MUTED_TEXT)
    c.setFont("Helvetica", 11)
    c.drawCentredString(center_x, 415, "THIS CERTIFICATE IS PROUDLY PRESENTED TO")

    # 5. Recipient Name
    c.setFillColor(COLOR_PRIMARY_NAVY)
    c.setFont("Helvetica-Bold", 26)
    c.drawCentredString(center_x, 372, recipient_name.strip())

    # Decorative underline for recipient name
    name_line_width = min(max(len(recipient_name) * 14, 240), 500)
    c.setStrokeColor(COLOR_LIGHT_ACCENT)
    c.setLineWidth(1)
    c.line(center_x - (name_line_width / 2), 358, center_x + (name_line_width / 2), 358)

    # 6. Description
    c.setFillColor(COLOR_MUTED_TEXT)
    c.setFont("Helvetica", 12)
    c.drawCentredString(
        center_x,
        328,
        "for successfully fulfilling all curriculum requirements and standards for",
    )

    # 7. Course / Event Name
    c.setFillColor(COLOR_DARK_TEXT)
    c.setFont("Helvetica-Bold", 19)
    c.drawCentredString(center_x, 295, course_name.strip())

    # 8. Extra Fields (if provided)
    if extra_fields and isinstance(extra_fields, dict):
        extra_items = [f"{k.replace('_', ' ').title()}: {v}" for k, v in extra_fields.items() if v is not None]
        if extra_items:
            extra_text = "   •   ".join(extra_items[:4])  # Render up to 4 items cleanly
            c.setFillColor(COLOR_MUTED_TEXT)
            c.setFont("Helvetica", 10)
            c.drawCentredString(center_x, 265, extra_text)

    # 9. Signatures and Verification Footer
    # Date Block (Left)
    c.setStrokeColor(COLOR_LIGHT_ACCENT)
    c.setLineWidth(1)
    c.line(90, 180, 260, 180)

    c.setFillColor(COLOR_DARK_TEXT)
    c.setFont("Helvetica-Bold", 11)
    c.drawCentredString(175, 192, str(issue_date).strip())

    c.setFillColor(COLOR_MUTED_TEXT)
    c.setFont("Helvetica", 9)
    c.drawCentredString(175, 162, "Date of Issuance")

    # Verification Seal Badge (Center)
    seal_y = 180
    c.setFillColor(COLOR_SEAL_BG)
    c.setStrokeColor(COLOR_SECONDARY_GOLD)
    c.setLineWidth(2)
    c.circle(center_x, seal_y, 30, fill=1, stroke=1)

    c.setLineWidth(0.8)
    c.circle(center_x, seal_y, 25, fill=0, stroke=1)

    c.setFillColor(COLOR_SECONDARY_GOLD)
    c.setFont("Helvetica-Bold", 7)
    c.drawCentredString(center_x, seal_y + 8, "VERIFIED")
    c.drawCentredString(center_x, seal_y - 2, "★ ★ ★")
    c.drawCentredString(center_x, seal_y - 12, "CREDENTIAL")

    # Signature Block (Right)
    c.setStrokeColor(COLOR_LIGHT_ACCENT)
    c.setLineWidth(1)
    c.line(page_width - 260, 180, page_width - 90, 180)

    c.setFillColor(COLOR_DARK_TEXT)
    c.setFont("Helvetica-Oblique", 12)
    c.drawCentredString(page_width - 175, 192, "Academic Program Director")

    c.setFillColor(COLOR_MUTED_TEXT)
    c.setFont("Helvetica", 9)
    c.drawCentredString(page_width - 175, 162, "Authorized Signature")

    # 10. Unique Certificate ID & Verification URL (Bottom Bar)
    c.setFillColor(COLOR_MUTED_TEXT)
    c.setFont("Helvetica", 8)
    footer_text = f"Certificate ID: {certificate_id}   |   Verified by Bulk Certificate Generator API"
    c.drawCentredString(center_x, 50, footer_text)

    # Save and finalize PDF canvas
    c.save()

    return str(pdf_path.resolve())
