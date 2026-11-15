"""Health check API router."""

from fastapi import APIRouter
from sqlalchemy import text

from app.core.config import settings
from app.database.session import SessionLocal

router = APIRouter()


def check_db() -> str:
    """Check database connectivity."""
    db = SessionLocal()
    try:
        db.execute(text("SELECT 1"))
        return "connected"
    except Exception:
        return "disconnected"
    finally:
        db.close()


@router.get("")
async def health() -> dict:
    """Health check endpoint with database connectivity check."""
    db_status = check_db()
    return {
        "status": "ok" if db_status == "connected" else "degraded",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "database": db_status,
    }


@router.get("/ready")
async def readiness() -> dict:
    """Readiness check endpoint."""
    db_status = check_db()
    return {
        "status": "ready" if db_status == "connected" else "not_ready",
        "service": settings.APP_NAME,
        "database": db_status,
    }
