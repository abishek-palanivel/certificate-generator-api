"""Pytest fixtures and test environment configuration."""

import shutil
import tempfile
from collections.abc import Generator
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.database import Base
from app.main import app


@pytest.fixture(scope="session")
def test_temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for test database and PDF artifacts."""
    temp_dir = Path(tempfile.mkdtemp(prefix="cert_api_test_"))
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture(scope="session")
def test_engine(test_temp_dir: Path):
    """Create a dedicated SQLite engine for testing."""
    test_db_path = test_temp_dir / "test_certificates.db"
    engine = create_engine(
        f"sqlite:///{test_db_path}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="session")
def TestingSessionLocal(test_engine):
    """Session factory bound to the test engine."""
    return sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=test_engine,
    )


@pytest.fixture(autouse=True)
def setup_test_environment(
    test_engine,
    TestingSessionLocal,
    test_temp_dir: Path,
    monkeypatch,
):
    """Configure storage paths and database sessionmaker for all tests."""
    # Direct storage directory to temporary location for tests
    test_storage = test_temp_dir / "certificates"
    test_storage.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(settings, "STORAGE_DIR", test_storage)

    # Monkeypatch SessionLocal across app modules so all components use test DB
    monkeypatch.setattr("app.database.SessionLocal", TestingSessionLocal)
    monkeypatch.setattr("app.services.job_processor.SessionLocal", TestingSessionLocal)

    # Clean tables before each test for clean isolation
    with test_engine.connect() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            conn.execute(table.delete())
        conn.commit()


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    """TestClient fixture executing requests against test database."""
    with TestClient(app) as test_client:
        yield test_client
