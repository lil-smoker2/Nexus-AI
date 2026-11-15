"""Conversation repository for NEXUS AI data access layer."""

from typing import List, Optional
from sqlalchemy.orm import Session
from app.database.models import Conversation, Message, User
from app.database.repositories.base import BaseRepository


class ConversationRepository(BaseRepository[Conversation]):
    def __init__(self, db: Session):
        super().__init__(Conversation, db)

    def get_by_user(self, user_id: str, skip: int = 0, limit: int = 100) -> List[Conversation]:
        return (
            self.db.query(Conversation)
            .filter(Conversation.user_id == user_id)
            .order_by(Conversation.updated_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def create_for_user(self, user_id: str, title: str = "New Conversation") -> Conversation:
        return self.create({
            "user_id": user_id,
            "title": title,
        })


class MessageRepository(BaseRepository[Message]):
    def __init__(self, db: Session):
        super().__init__(Message, db)

    def get_by_conversation(
        self, conversation_id: str, skip: int = 0, limit: int = 100
    ) -> List[Message]:
        return (
            self.db.query(Message)
            .filter(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.asc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def create_message(
        self,
        conversation_id: str,
        user_id: str,
        role: str,
        content: str,
        metadata: Optional[dict] = None,
    ) -> Message:
        return self.create({
            "conversation_id": conversation_id,
            "user_id": user_id,
            "role": role,
            "content": content,
            "metadata_": metadata,
        })
