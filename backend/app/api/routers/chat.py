"""Chat API router with persistent database storage.

Chat/model interaction is isolated from MCP servers, execution engine internals,
and other optional subsystems: failures there must not prevent basic conversation.
"""

import logging
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database.repositories.container import Repositories
from app.database.session import get_db

router = APIRouter()
logger = logging.getLogger(__name__)


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


async def _generate_chat_reply(model_messages: List[dict]) -> str:
    """Direct model-service chat path (fallback/isolation from orchestration)."""
    from app.models.schemas import GenerationRequest
    from app.services.model_service import model_service

    resp = await model_service.generate(
        GenerationRequest(messages=model_messages, temperature=0.7)
    )
    content = (resp.content or "").strip() if resp else ""
    return content or "I’m here, but I couldn’t generate a response right now."


@router.post("/messages", response_model=SendMessageResponse)
async def send_message(
    request: SendMessageRequest,
    repos: Repositories = Depends(get_repos),
) -> SendMessageResponse:
    conversation = repos.conversations.get(request.conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    user_id = get_or_create_default_user(repos)

    # Persist user message
    repos.messages.create_message(
        conversation_id=request.conversation_id,
        user_id=user_id,
        role="user",
        content=request.content,
    )

    # Build conversation history for the model (last 20 messages for context)
    prior_messages = repos.messages.get_by_conversation(request.conversation_id)
    model_messages: List[dict] = [
        {
            "role": "system",
            "content": "You are NEXUS AI, a helpful personal assistant and conversational companion. Be concise, natural, and supportive.",
        }
    ]
    for msg in prior_messages[-20:]:
        model_messages.append({"role": msg.role, "content": msg.content})

    execution = None
    reply: Optional[str] = None

    # Optional: record execution and try orchestrated agent path, but never let it break chat
    try:
        from app.agents.base import AgentContext, AgentType
        from app.orchestration.orchestrator import orchestrator

        try:
            execution = repos.executions.create_execution(
                agent_id=getattr(AgentType, "COMPANION", "companion").value
                if hasattr(getattr(AgentType, "COMPANION", None), "value")
                else "companion",
                user_objective=request.content,
                conversation_id=request.conversation_id,
            )
        except Exception:
            execution = None

        context = AgentContext(
            execution_id=execution.id if execution else "chat-direct",
            agent_type=getattr(AgentType, "COMPANION", "companion"),
            conversation_id=request.conversation_id,
            user_id=user_id,
            messages=[m for m in model_messages if m.get("role") != "system"],
        )
        result = await orchestrator.route(context)
        if result and getattr(result, "success", False) and getattr(result, "message", None):
            reply = result.message
            if execution:
                try:
                    repos.executions.update(
                        execution.id, {"status": "completed", "final_report": reply}
                    )
                except Exception:
                    pass
        else:
            if execution:
                try:
                    repos.executions.update(
                        execution.id,
                        {
                            "status": "failed",
                            "final_report": getattr(result, "message", "Agent returned no response"),
                        },
                    )
                except Exception:
                    pass
    except Exception as exc:
        logger.warning("Chat orchestration path failed, falling back to direct model: %s", exc)
        if execution:
            try:
                repos.executions.update(
                    execution.id, {"status": "failed", "final_report": f"Orchestration error: {exc}"}
                )
            except Exception:
                pass

    # Fallback: direct model generation (keeps chat working even if agents/MCP/execution fail)
    if not reply:
        try:
            reply = await _generate_chat_reply(model_messages)
        except Exception as exc:
            logger.exception("Chat model fallback failed: %s", exc)
            raise HTTPException(
                status_code=503,
                detail="Chat is temporarily unavailable (model unavailable). Other systems may be affected, but chat can retry shortly.",
            )

    assistant_msg = repos.messages.create_message(
        conversation_id=request.conversation_id,
        user_id=user_id,
        role="assistant",
        content=reply,
    )

    try:
        repos.conversations.update(request.conversation_id, {"updated_at": datetime.utcnow()})
    except Exception:
        pass

    return SendMessageResponse(conversation_id=request.conversation_id, message=assistant_msg)
