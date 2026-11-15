"""Model management API router.

Endpoints:
- GET /api/v1/models          - List all available models across providers
- GET /api/v1/providers       - List all providers with availability
- POST /api/v1/models/select  - Select an active model
- POST /api/v1/models/generate - Generate a response (direct model call)
- GET  /api/v1/models/active  - Get the currently active model
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Any, Dict, List, Optional

from app.services.model_service import model_service

router = APIRouter()


class GenerateRequest(BaseModel):
    model_id: Optional[str] = None
    messages: List[Dict[str, Any]]
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    stream: bool = False


class GenerateResponse(BaseModel):
    content: str
    role: str = "assistant"
    model: str
    finish_reason: Optional[str] = None
    usage: Dict[str, int] = {}


@router.get("")
async def list_models():
    """List all available models across all providers."""
    return await model_service.list_models()


@router.get("/providers")
async def list_providers():
    """List all providers with availability and model counts."""
    return await model_service.list_providers()


@router.get("/active")
async def get_active_model():
    """Get the currently active model."""
    active_id = model_service.get_active_model_id()
    provider = model_service.get_active_provider()
    if not active_id or not provider:
        raise HTTPException(status_code=404, detail="No active model")
    return {"model_id": active_id, "provider": provider.provider_name}


@router.post("/select")
async def select_model(request: dict):
    """Select a model to use for generation."""
    model_id = request.get("model_id")
    if not model_id:
        raise HTTPException(status_code=400, detail="model_id is required")
    from app.models.schemas import ModelSelectRequest
    return await model_service.select_model(ModelSelectRequest(model_id=model_id))


@router.post("/generate", response_model=GenerateResponse)
async def generate(request: GenerateRequest):
    """Generate a response using the active (or specified) model."""
    from app.models.schemas import GenerationRequest
    gen_request = GenerationRequest(
        model_id=request.model_id,
        messages=request.messages,
        temperature=request.temperature,
        max_tokens=request.max_tokens,
        stream=request.stream,
    )
    return await model_service.generate(gen_request)
