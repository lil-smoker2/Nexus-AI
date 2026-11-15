"""Health check API router."""

from fastapi import APIRouter

from app.core.config import settings

router = APIRouter()


@router.get("")
async def health() -> dict:
    """Health check endpoint."""
    return {
        "status": "ok",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
    }


@router.get("/ready")
async def readiness() -> dict:
    """Readiness check endpoint."""
    return {
        "status": "ready",
        "service": settings.APP_NAME,
    }
