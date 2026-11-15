"""Task repository for NEXUS AI data access layer."""

from typing import List, Optional
from sqlalchemy.orm import Session
from app.database.models import Task
from app.database.repositories.base import BaseRepository


class TaskRepository(BaseRepository[Task]):
    def __init__(self, db: Session):
        super().__init__(Task, db)

    def get_by_execution(self, execution_id: str) -> List[Task]:
        return (
            self.db.query(Task)
            .filter(Task.execution_id == execution_id)
            .order_by(Task.created_at.asc())
            .all()
        )

    def get_by_status(self, status: str, skip: int = 0, limit: int = 100) -> List[Task]:
        return (
            self.db.query(Task)
            .filter(Task.status == status)
            .order_by(Task.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_subtasks(self, parent_task_id: str) -> List[Task]:
        return (
            self.db.query(Task)
            .filter(Task.parent_task_id == parent_task_id)
            .order_by(Task.created_at.asc())
            .all()
        )
