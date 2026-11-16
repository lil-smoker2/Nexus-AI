"""Execution repository for NEXUS AI data access layer."""

from typing import List, Optional
from sqlalchemy.orm import Session
from app.database.models import Execution
from app.database.repositories.base import BaseRepository


class ExecutionRepository(BaseRepository[Execution]):
    def __init__(self, db: Session):
        super().__init__(Execution, db)

    def create_execution(
        self,
        agent_id: str,
        user_objective: str,
        conversation_id: Optional[str] = None,
    ) -> Execution:
        return self.create(
            {
                "agent_id": agent_id,
                "user_objective": user_objective,
                "conversation_id": conversation_id,
                "status": "pending",
            }
        )

    def list(self, skip: int = 0, limit: int = 100) -> List[Execution]:
        return (
            self.db.query(Execution)
            .order_by(Execution.updated_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_by_agent(self, agent_id: str, skip: int = 0, limit: int = 100) -> List[Execution]:
        return (
            self.db.query(Execution)
            .filter(Execution.agent_id == agent_id)
            .order_by(Execution.updated_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_by_status(self, status: str, skip: int = 0, limit: int = 100) -> List[Execution]:
        return (
            self.db.query(Execution)
            .filter(Execution.status == status)
            .order_by(Execution.updated_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_by_conversation(self, conversation_id: str) -> List[Execution]:
        return (
            self.db.query(Execution)
            .filter(Execution.conversation_id == conversation_id)
            .order_by(Execution.created_at.desc())
            .all()
        )
