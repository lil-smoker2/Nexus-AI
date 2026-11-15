"""MCP server repository for NEXUS AI data access layer."""

from typing import List, Optional
from sqlalchemy.orm import Session
from app.database.models import McpServer
from app.database.repositories.base import BaseRepository


class McpServerRepository(BaseRepository[McpServer]):
    def __init__(self, db: Session):
        super().__init__(McpServer, db)

    def get_by_name(self, name: str) -> Optional[McpServer]:
        return self.db.query(McpServer).filter(McpServer.name == name).first()

    def get_by_status(self, status: str) -> List[McpServer]:
        return (
            self.db.query(McpServer)
            .filter(McpServer.connection_state == status)
            .all()
        )

    def update_status(self, server_id: str, status: str) -> Optional[McpServer]:
        return self.update(server_id, {"connection_state": status})
