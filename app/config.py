"""Application configuration and environment settings."""

import os
from pathlib import Path

# Base project directory
BASE_DIR = Path(__file__).resolve().parent.parent


class Settings:
    """Project configuration settings with environment variable fallbacks."""

    PROJECT_NAME: str = "Bulk Certificate Generator API"
    VERSION: str = "1.0.0"
    DESCRIPTION: str = (
        "High-performance backend API for asynchronous bulk certificate generation, "
        "tracking, and distribution using FastAPI, SQLAlchemy, and ReportLab."
    )

    # Database configuration (SQLite default, can be overridden by environment variable)
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        f"sqlite:///{BASE_DIR / 'certificates.db'}"
    )

    # Storage directory for generated PDF certificates
    STORAGE_DIR: Path = Path(
        os.getenv("STORAGE_DIR", str(BASE_DIR / "generated_certificates"))
    )

    # Job and input validation limits
    MAX_RECIPIENTS_PER_JOB: int = int(os.getenv("MAX_RECIPIENTS_PER_JOB", "500"))
    MAX_NAME_LENGTH: int = 100
    MAX_EMAIL_LENGTH: int = 255
    MAX_COURSE_LENGTH: int = 150


settings = Settings()

# Ensure the storage directory exists on disk
settings.STORAGE_DIR.mkdir(parents=True, exist_ok=True)
