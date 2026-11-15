"""Version API router."""

from fastapi import APIRouter

from app.core.config import settings

router = APIRouter()


@router.get("")
async def version() -> dict:
    """Return application version."""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
    }
