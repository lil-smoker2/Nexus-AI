"""FastAPI application factory for NEXUS AI backend."""

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.core.config import settings
from app.api.routers import health, version, chat
from app.database.session import SessionLocal, get_db, init_db
from app.database.repositories.container import Repositories


def get_repositories(db: Session = Depends(get_db)) -> Repositories:
    """Dependency that provides a Repositories container with a DB session."""
    return Repositories(db)


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        debug=settings.DEBUG,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.on_event("startup")
    def on_startup():
        init_db()

    app.include_router(health.router, prefix="/health", tags=["health"])
    app.include_router(version.router, prefix="/version", tags=["version"])
    app.include_router(chat.router, prefix="/api/v1/chat", tags=["chat"])

    @app.get("/")
    async def root():
        return {
            "name": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "status": "running",
        }

    return app


app = create_app()
