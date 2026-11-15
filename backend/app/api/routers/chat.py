"""Chat API router with persistent database storage."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.database.repositories.container import Repositories

router = APIRouter()


def get_repos(db: Session = Depends(get_db)) -> Repositories:
    return Repositories(db)


class Message(BaseModel):
    id: str
    conversation_id: str
    role: str
    content: str
    created_at: datetime
    metadata_: Optional[dict] = None

    class Config:
        from_attributes = True


class Conversation(BaseModel):
    id: str
    user_id: str
    title: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SendMessageRequest(BaseModel):
    conversation_id: str
    content: str


class SendMessageResponse(BaseModel):
    conversation_id: str
    message: Message


def get_or_create_default_user(repos: Repositories) -> str:
    user = repos.users.get_by_username("default")
    if not user:
        user = repos.users.create_user("default")
    return user.id


@router.get("", response_model=List[Conversation])
async def list_conversations(repos: Repositories = Depends(get_repos)) -> List[Conversation]:
    user_id = get_or_create_default_user(repos)
    return repos.conversations.get_by_user(user_id)


@router.post("", response_model=Conversation)
async def create_conversation(
    title: str = "New Conversation",
    repos: Repositories = Depends(get_repos),
) -> Conversation:
    user_id = get_or_create_default_user(repos)
    return repos.conversations.create_for_user(user_id, title)


@router.get("/{conversation_id}/messages", response_model=List[Message])
async def get_messages(
    conversation_id: str,
    repos: Repositories = Depends(get_repos),
) -> List[Message]:
    conversation = repos.conversations.get(conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return repos.messages.get_by_conversation(conversation_id)


@router.post("/messages", response_model=SendMessageResponse)
async def send_message(
    request: SendMessageRequest,
    repos: Repositories = Depends(get_repos),
) -> SendMessageResponse:
    conversation = repos.conversations.get(request.conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    user_id = get_or_create_default_user(repos)

    repos.messages.create_message(
        conversation_id=request.conversation_id,
        user_id=user_id,
        role="user",
        content=request.content,
    )

    assistant_content = f"I received your message: '{request.content}'. Model integration coming in Phase 4."
    assistant_msg = repos.messages.create_message(
        conversation_id=request.conversation_id,
        user_id=user_id,
        role="assistant",
        content=assistant_content,
    )

    repos.conversations.update(request.conversation_id, {"updated_at": datetime.utcnow()})

    return SendMessageResponse(conversation_id=request.conversation_id, message=assistant_msg)
