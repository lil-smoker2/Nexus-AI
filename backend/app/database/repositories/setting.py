"""Setting repository for NEXUS AI data access layer."""

from typing import List, Optional
from sqlalchemy.orm import Session
from app.database.models import Setting
from app.database.repositories.base import BaseRepository


class SettingRepository(BaseRepository[Setting]):
    def __init__(self, db: Session):
        super().__init__(Setting, db)

    def get_by_user_and_key(self, user_id: str, key: str) -> Optional[Setting]:
        return (
            self.db.query(Setting)
            .filter(Setting.user_id == user_id, Setting.key == key)
            .first()
        )

    def get_by_user(self, user_id: str) -> List[Setting]:
        return (
            self.db.query(Setting)
            .filter(Setting.user_id == user_id)
            .all()
        )

    def set(self, user_id: str, key: str, value: str) -> Setting:
        existing = self.get_by_user_and_key(user_id, key)
        if existing:
            return self.update(existing.id, {"value": value})
        return self.create({"user_id": user_id, "key": key, "value": value})

    def get(self, user_id: str, key: str) -> Optional[str]:
        setting = self.get_by_user_and_key(user_id, key)
        return setting.value if setting else None
