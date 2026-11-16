"""Chat API router with persistent database storage."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.database.repositories.container import Repositories
from app.orchestration.orchestrator import orchestrator
from app.agents.base import AgentContext, AgentType

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

    # Build conversation history for the agent (last 10 messages)
    prior_messages = repos.messages.get_by_conversation(request.conversation_id)
    model_messages: List[dict] = [
        {"role": "system", "content": "You are NEXUS AI, a helpful personal assistant. Be concise and natural."}
    ]
    for msg in prior_messages[-10:]:
        model_messages.append({"role": msg.role, "content": msg.content})

    # Create execution record
    execution = repos.executions.create_execution(
        agent_id=AgentType.COMPANION.value,
        user_objective=request.content,
        conversation_id=request.conversation_id,
    )

    context = AgentContext(
        execution_id=execution.id,
        agent_type=AgentType.COMPANION,
        conversation_id=request.conversation_id,
        user_id=user_id,
        messages=model_messages[1:],  # exclude system for context; agent adds its own system
    )

    result = await orchestrator.route(context)

    if not result.success:
        repos.executions.update(execution.id, {"status": "failed", "final_report": result.message})
        raise HTTPException(status_code=500, detail=result.message)

    repos.executions.update(
        execution.id,
        {"status": "completed", "final_report": result.message},
    )

    assistant_msg = repos.messages.create_message(
        conversation_id=request.conversation_id,
        user_id=user_id,
        role="assistant",
        content=result.message,
    )

    repos.conversations.update(request.conversation_id, {"updated_at": datetime.utcnow()})

    return SendMessageResponse(conversation_id=request.conversation_id, message=assistant_msg)
