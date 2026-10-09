"""Main FastAPI application entrypoint."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator
from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import init_db
from app.routes.certificates import router as certificates_router
from app.routes.jobs import router as jobs_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan context manager for startup and shutdown routines."""
    # Ensure database schema is created
    init_db()
    # Ensure storage directory exists
    settings.STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description=settings.DESCRIPTION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Enable CORS for web frontend clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routes grouped under /api prefix
api_router = APIRouter(prefix="/api")
api_router.include_router(jobs_router)
api_router.include_router(certificates_router)


@api_router.get("/health", tags=["Health"])
def health_check() -> dict[str, str]:
    """Health check endpoint to verify service readiness."""
    return {"status": "ok", "service": settings.PROJECT_NAME, "version": settings.VERSION}


app.include_router(api_router)


@app.get("/", tags=["Root"])
def root() -> dict[str, str]:
    """API welcome and navigation endpoint."""
    return {
        "message": f"Welcome to {settings.PROJECT_NAME}",
        "documentation": "/docs",
        "health": "/api/health",
    }
