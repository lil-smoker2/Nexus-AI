"""MCP server repository for NEXUS AI data access layer."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from app.database.models import McpServer, McpAuditEvent
from app.database.repositories.base import BaseRepository


class McpServerRepository(BaseRepository[McpServer]):
    def __init__(self, db: Session):
        super().__init__(McpServer, db)

    def get_by_name(self, name: str) -> Optional[McpServer]:
        return self.db.query(McpServer).filter(McpServer.name == name).first()

    def get_by_status(self, status: str) -> List[McpServer]:
        return self.db.query(McpServer).filter(McpServer.connection_state == status).all()

    def update_status(self, server_id: str, status: str) -> Optional[McpServer]:
        return self.update(server_id, {"connection_state": status, "updated_at": datetime.utcnow()})

    def upsert_by_name(self, name: str, data: Dict[str, Any]) -> McpServer:
        existing = self.get_by_name(name)
        payload = {**data}
        payload.setdefault("name", name)
        if existing:
            for k, v in payload.items():
                setattr(existing, k, v)
            existing.updated_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(existing)
            return existing
        obj = McpServer(**payload)
        self.db.add(obj)
        self.db.commit()
        self.db.refresh(obj)
        return obj

    def list_all(self) -> List[McpServer]:
        return self.db.query(McpServer).order_by(McpServer.created_at.asc()).all()


class McpAuditRepository(BaseRepository[McpAuditEvent]):
    def __init__(self, db: Session):
        super().__init__(McpAuditEvent, db)

    def log(self, **fields: Any) -> McpAuditEvent:
        obj = McpAuditEvent(**fields)
        self.db.add(obj)
        self.db.commit()
        self.db.refresh(obj)
        return obj

    def recent(self, limit: int = 100, server_id: Optional[str] = None) -> List[McpAuditEvent]:
        q = self.db.query(McpAuditEvent)
        if server_id:
            q = q.filter(McpAuditEvent.server_id == server_id)
        return q.order_by(McpAuditEvent.created_at.desc()).limit(max(1, min(limit, 1000))).all()

