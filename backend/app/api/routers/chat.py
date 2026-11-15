"""Chat API router."""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import uuid

router = APIRouter()


class Message(BaseModel):
    id: str
    conversation_id: str
    role: str  # user, assistant, system, tool
    content: str
    created_at: str
    metadata: Optional[dict] = None


class Conversation(BaseModel):
    id: str
    user_id: str
    title: str
    created_at: str
    updated_at: str


class SendMessageRequest(BaseModel):
    conversation_id: str
    content: str


class SendMessageResponse(BaseModel):
    conversation_id: str
    message: Message


# In-memory store for Phase 2 (will be replaced by database in Phase 3)
_conversations: dict[str, Conversation] = {}
_messages: dict[str, List[Message]] = {}


@router.get("", response_model=List[Conversation])
async def list_conversations() -> List[Conversation]:
    return list(_conversations.values())


@router.post("", response_model=Conversation)
async def create_conversation(title: str = "New Conversation") -> Conversation:
    conv = Conversation(
        id=str(uuid.uuid4()),
        user_id="default",
        title=title,
        created_at=datetime.utcnow().isoformat(),
        updated_at=datetime.utcnow().isoformat(),
    )
    _conversations[conv.id] = conv
    _messages[conv.id] = []
    return conv


@router.get("/{conversation_id}/messages", response_model=List[Message])
async def get_messages(conversation_id: str) -> List[Message]:
    return _messages.get(conversation_id, [])


@router.post("/messages", response_model=SendMessageResponse)
async def send_message(request: SendMessageRequest) -> SendMessageResponse:
    conv_id = request.conversation_id
    if conv_id not in _conversations:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Conversation not found")

    user_msg = Message(
        id=str(uuid.uuid4()),
        conversation_id=conv_id,
        role="user",
        content=request.content,
        created_at=datetime.utcnow().isoformat(),
    )
    _messages.setdefault(conv_id, []).append(user_msg)

    # Echo response for Phase 2 (will be replaced by model integration in Phase 4)
    assistant_msg = Message(
        id=str(uuid.uuid4()),
        conversation_id=conv_id,
        role="assistant",
        content=f"I received your message: '{request.content}'. Model integration coming in Phase 4.",
        created_at=datetime.utcnow().isoformat(),
    )
    _messages[conv_id].append(assistant_msg)

    # Update conversation timestamp
    conv = _conversations[conv_id]
    conv.updated_at = datetime.utcnow().isoformat()

    return SendMessageResponse(conversation_id=conv_id, message=assistant_msg)
