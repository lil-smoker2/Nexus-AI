"""Abstract base class and data models for model providers.

Defines a provider-independent interface covering:
- Text generation and streaming
- Structured output
- Tool-call requests
- Context-window metadata
- Token usage where available
- Cancellation, timeouts, retries
- Model capability declarations
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Dict, List, Optional


@dataclass
class ModelMessage:
    """A message in a conversation, provider-agnostic."""

    role: str  # system, user, assistant, tool
    content: str
    name: Optional[str] = None
    tool_call_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ToolCall:
    """A tool call requested by the model."""

    id: str
    name: str
    arguments: Dict[str, Any]


@dataclass
class ModelResponse:
    """A response from a model provider."""

    content: str
    role: str = "assistant"
    tool_calls: List[ToolCall] = field(default_factory=list)
    finish_reason: Optional[str] = None
    usage: Dict[str, int] = field(default_factory=dict)
    model: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ModelInfo:
    """Describes a model's capabilities and configuration."""

    id: str
    name: str
    provider: str
    context_window: int
    supports_streaming: bool = False
    supports_tools: bool = False
    supports_structured_output: bool = False
    is_local: bool = False
    is_available: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GenerationConfig:
    """Configuration for a generation request."""

    temperature: float = 0.7
    max_tokens: Optional[int] = None
    top_p: Optional[float] = None
    top_k: Optional[int] = None
    stop_sequences: List[str] = field(default_factory=list)
    stream: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


class ModelProviderError(Exception):
    """Base exception for model provider errors."""

    pass


class ModelProvider(ABC):
    """Abstract base class for model providers.

    All providers must implement:
    - list_models: discover available models
    - generate: produce a single response
    - stream: produce a streaming response (optional; default falls back to generate)
    """

    def __init__(self, provider_name: str, config: Optional[Dict[str, Any]] = None):
        self.provider_name = provider_name
        self.config = config or {}
        self._initialized = False

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the provider (load model, establish connection, etc.)."""

    @abstractmethod
    async def list_models(self) -> List[ModelInfo]:
        """Return available models from this provider."""

    @abstractmethod
    async def generate(
        self,
        messages: List[ModelMessage],
        config: Optional[GenerationConfig] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> ModelResponse:
        """Generate a single (non-streaming) response."""

    async def stream(
        self,
        messages: List[ModelMessage],
        config: Optional[GenerationConfig] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> AsyncIterator[ModelResponse]:
        """Generate a streaming response.

        Default implementation wraps `generate` into a single yield.
        Providers that support streaming should override this.
        """
        response = await self.generate(messages, config, tools)
        yield response

    @abstractmethod
    async def is_available(self) -> bool:
        """Check if the provider is available (model loaded, API reachable, etc.)."""

    async def shutdown(self) -> None:
        """Clean up provider resources."""
        self._initialized = False

    @property
    def is_initialized(self) -> bool:
        return self._initialized
