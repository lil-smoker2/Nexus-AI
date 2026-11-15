"""Pydantic schemas for model management API."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ModelInfo(BaseModel):
    id: str
    name: str
    provider: str
    context_window: int
    supports_streaming: bool = False
    supports_tools: bool = False
    supports_structured_output: bool = False
    is_local: bool = False
    is_available: bool = False
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ModelListResponse(BaseModel):
    models: List[ModelInfo]
    active_model: Optional[str] = None


class ModelSelectRequest(BaseModel):
    model_id: str


class ModelSelectResponse(BaseModel):
    model_id: str
    provider: str
    status: str  # "selected", "loaded", "failed"


class GenerationRequest(BaseModel):
    model_id: Optional[str] = None
    messages: List[Dict[str, Any]]
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    stream: bool = False


class GenerationResponse(BaseModel):
    content: str
    role: str = "assistant"
    model: str
    finish_reason: Optional[str] = None
    usage: Dict[str, int] = Field(default_factory=dict)


class ProviderInfo(BaseModel):
    name: str
    type: str  # "local" / "cloud"
    is_available: bool
    models: List[str] = Field(default_factory=list)


class ProvidersResponse(BaseModel):
    providers: List[ProviderInfo]
