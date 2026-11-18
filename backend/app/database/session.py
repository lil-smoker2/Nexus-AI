"""SQLAlchemy database setup for NEXUS AI backend."""

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker, Session

from app.core.config import settings
from app.database.models import Base

engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Session:
    """FastAPI dependency that yields a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create all tables and apply lightweight compatibility migrations."""
    Base.metadata.create_all(bind=engine)
    _ensure_mcp_schema()


def _ensure_mcp_schema() -> None:
    """Best-effort schema evolution for MCP tables on existing SQLite DBs."""
    if "sqlite" not in settings.DATABASE_URL:
        return
    try:
        insp = inspect(engine)
        tables = set(insp.get_table_names())
        if "mcp_servers" in tables:
            cols = {c["name"] for c in insp.get_columns("mcp_servers")}
            stmts = []
            if "config" not in cols:
                stmts.append("ALTER TABLE mcp_servers ADD COLUMN config JSON")
            if "enabled" not in cols:
                stmts.append("ALTER TABLE mcp_servers ADD COLUMN enabled BOOLEAN DEFAULT 1")
            if "last_error" not in cols:
                stmts.append("ALTER TABLE mcp_servers ADD COLUMN last_error TEXT")
            if "last_connected_at" not in cols:
                stmts.append("ALTER TABLE mcp_servers ADD COLUMN last_connected_at DATETIME")
            if "server_info" not in cols:
                stmts.append("ALTER TABLE mcp_servers ADD COLUMN server_info JSON")
            if "capabilities" not in cols:
                stmts.append("ALTER TABLE mcp_servers ADD COLUMN capabilities JSON")
            if stmts:
                with engine.begin() as conn:
                    for s in stmts:
                        conn.execute(text(s))
    except Exception:
        # Do not block startup on best-effort migration
        pass

