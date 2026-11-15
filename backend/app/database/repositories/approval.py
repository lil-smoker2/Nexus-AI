"""Approval repository for NEXUS AI data access layer."""

from typing import List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from app.database.models import Approval
from app.database.repositories.base import BaseRepository


class ApprovalRepository(BaseRepository[Approval]):
    def __init__(self, db: Session):
        super().__init__(Approval, db)

    def get_pending(self, user_id: str) -> List[Approval]:
        return (
            self.db.query(Approval)
            .filter(Approval.user_id == user_id, Approval.decision == "requested")
            .order_by(Approval.created_at.desc())
            .all()
        )

    def get_by_execution(self, execution_id: str) -> List[Approval]:
        return (
            self.db.query(Approval)
            .filter(Approval.execution_id == execution_id)
            .order_by(Approval.created_at.desc())
            .all()
        )

    def decide(self, approval_id: str, decision: str) -> Optional[Approval]:
        return self.update(approval_id, {"decision": decision, "decided_at": datetime.utcnow()})
