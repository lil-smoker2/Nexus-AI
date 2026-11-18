"""FastAPI application factory for NEXUS AI backend."""

import asyncio

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.core.config import settings
from app.api.routers import health, version, chat, models, executions, mcp, tasks
from app.database.session import SessionLocal, get_db, init_db
from app.database.repositories.container import Repositories
from app.services.model_service import model_service
from app.mcp.manager import mcp_manager


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
    async def on_startup():
        # Core persistence must be available for chat/history
        try:
            init_db()
        except Exception:
            pass
        # Model service is needed for chat; initialize best-effort without blocking app startup
        try:
            await model_service.initialize()
        except Exception:
            pass
        # MCP/tooling subsystems are optional for basic chat; failures must not break chat availability
        try:
            mcp_manager.initialize()
        except Exception:
            pass

    @app.on_event("shutdown")
    async def on_shutdown():
        try:
            await model_service.shutdown()
        except Exception:
            pass
        try:
            mcp_manager.shutdown()
        except Exception:
            pass

    app.include_router(health.router, prefix="/health", tags=["health"])
    app.include_router(version.router, prefix="/version", tags=["version"])
    app.include_router(chat.router, prefix="/api/v1/chat", tags=["chat"])
    app.include_router(models.router, prefix="/api/v1/models", tags=["models"])
    app.include_router(executions.router, prefix="/api/v1/executions", tags=["executions"])
    app.include_router(tasks.router, prefix="/api/v1/tasks", tags=["tasks"])
    app.include_router(mcp.router, prefix="/api/v1/mcp", tags=["mcp"])

    @app.get("/")
    async def root():
        return {
            "name": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "status": "running",
        }

    return app


app = create_app()
