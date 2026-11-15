"""Memory repository for NEXUS AI data access layer."""

from typing import List, Optional
from sqlalchemy.orm import Session
from app.database.models import Memory
from app.database.repositories.base import BaseRepository


class MemoryRepository(BaseRepository[Memory]):
    def __init__(self, db: Session):
        super().__init__(Memory, db)

    def get_by_user(
        self, user_id: str, category: Optional[str] = None, skip: int = 0, limit: int = 100
    ) -> List[Memory]:
        query = self.db.query(Memory).filter(Memory.user_id == user_id)
        if category:
            query = query.filter(Memory.category == category)
        return query.order_by(Memory.importance.desc(), Memory.created_at.desc()).offset(skip).limit(limit).all()

    def get_by_category(self, user_id: str, category: str) -> List[Memory]:
        return (
            self.db.query(Memory)
            .filter(Memory.user_id == user_id, Memory.category == category)
            .order_by(Memory.importance.desc(), Memory.created_at.desc())
            .all()
        )
