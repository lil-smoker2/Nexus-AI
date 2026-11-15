"""OpenAI-compatible model provider adapter.

Supports OpenAI API and any OpenAI-compatible endpoint (Ollama, LocalAI,
vLLM, LiteLLM, etc.) via a configurable base URL and API key.
"""

import os
from typing import Any, AsyncIterator, Dict, List, Optional

try:
    from openai import AsyncOpenAI
    from openai.types.chat import ChatCompletionMessageParam
    HAS_OPENAI = True
except ImportError:  # pragma: no cover - openai may not be installed
    HAS_OPENAI = False

from app.models.providers.base import (
    GenerationConfig,
    ModelInfo,
    ModelMessage,
    ModelProvider,
    ModelProviderError,
    ModelResponse,
    ToolCall,
)


class OpenAICompatibleProvider(ModelProvider):
    """Adapter for OpenAI and OpenAI-compatible APIs."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__("openai-compatible", config or {})
        self._client: Optional[Any] = None
        self._api_key: Optional[str] = None
        self._base_url: Optional[str] = None
        self._default_model: Optional[str] = None

    async def initialize(self) -> None:
        if not HAS_OPENAI:
            raise ModelProviderError(
                "openai package is not installed. Install with: pip install openai"
            )
        self._api_key = self.config.get("api_key") or os.getenv("OPENAI_API_KEY")
        self._base_url = self.config.get("base_url") or os.getenv("OPENAI_BASE_URL")
        self._default_model = self.config.get("default_model") or os.getenv(
            "OPENAI_DEFAULT_MODEL", "gpt-3.5-turbo"
        )
        self._client = AsyncOpenAI(api_key=self._api_key, base_url=self._base_url)
        self._initialized = True

    async def list_models(self) -> List[ModelInfo]:
        if not self._client:
            return []
        try:
            models = await self._client.models.list()
            infos: List[ModelInfo] = []
            for m in models.data:
                mid = m.id
                infos.append(
                    ModelInfo(
                        id=mid,
                        name=mid,
                        provider="openai-compatible",
                        context_window=4096,
                        supports_streaming=True,
                        supports_tools=True,
                        supports_structured_output=True,
                        is_local=False,
                        is_available=True,
                    )
                )
            return infos
        except Exception:
            return []

    async def generate(
        self,
        messages: List[ModelMessage],
        config: Optional[GenerationConfig] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> ModelResponse:
        if not self._client:
            raise ModelProviderError("OpenAI provider not initialized")

        cfg = config or GenerationConfig()
        openai_messages = self._to_openai_messages(messages)

        kwargs: Dict[str, Any] = {
            "model": self._default_model,
            "messages": openai_messages,
            "temperature": cfg.temperature,
        }
        if cfg.max_tokens:
            kwargs["max_tokens"] = cfg.max_tokens
        if cfg.top_p is not None:
            kwargs["top_p"] = cfg.top_p
        if cfg.stop_sequences:
            kwargs["stop"] = cfg.stop_sequences
        if cfg.stream:
            kwargs["stream"] = True

        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        try:
            response = await self._client.chat.completions.create(**kwargs)
        except Exception as exc:
            raise ModelProviderError(f"OpenAI API error: {exc}") from exc

        if cfg.stream:
            # Non-streaming path should not be reached when stream=True;
            # collect the stream for a single response.
            content_parts: List[str] = []
            tool_calls: List[ToolCall] = []
            finish_reason: Optional[str] = None
            async for chunk in response:
                choice = chunk.choices[0]
                delta = choice.delta
                if delta.content:
                    content_parts.append(delta.content)
                if delta.tool_calls:
                    for tc in delta.tool_calls:
                        tool_calls.append(
                            ToolCall(
                                id=tc.id or "",
                                name=tc.function.name or "",
                                arguments={},
                            )
                        )
                if choice.finish_reason:
                    finish_reason = choice.finish_reason
            return ModelResponse(
                content="".join(content_parts),
                role="assistant",
                tool_calls=tool_calls,
                finish_reason=finish_reason,
                model=self._default_model,
            )

        choice = response.choices[0]
        msg = choice.message
        tool_calls: List[ToolCall] = []
        if msg.tool_calls:
            for tc in msg.tool_calls:
                tool_calls.append(
                    ToolCall(
                        id=tc.id,
                        name=tc.function.name,
                        arguments={},
                    )
                )

        usage: Dict[str, int] = {}
        if response.usage:
            usage = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            }

        return ModelResponse(
            content=msg.content or "",
            role="assistant",
            tool_calls=tool_calls,
            finish_reason=choice.finish_reason,
            usage=usage,
            model=self._default_model,
        )

    async def stream(
        self,
        messages: List[ModelMessage],
        config: Optional[GenerationConfig] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> AsyncIterator[ModelResponse]:
        if not self._client:
            raise ModelProviderError("OpenAI provider not initialized")

        cfg = config or GenerationConfig()
        cfg.stream = True
        openai_messages = self._to_openai_messages(messages)

        kwargs: Dict[str, Any] = {
            "model": self._default_model,
            "messages": openai_messages,
            "temperature": cfg.temperature,
            "stream": True,
        }
        if cfg.max_tokens:
            kwargs["max_tokens"] = cfg.max_tokens
        if cfg.top_p is not None:
            kwargs["top_p"] = cfg.top_p
        if cfg.stop_sequences:
            kwargs["stop"] = cfg.stop_sequences
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        try:
            stream = await self._client.chat.completions.create(**kwargs)
        except Exception as exc:
            raise ModelProviderError(f"OpenAI API error: {exc}") from exc

        async for chunk in stream:
            choice = chunk.choices[0]
            delta = choice.delta
            content = delta.content or ""
            tool_calls: List[ToolCall] = []
            if delta.tool_calls:
                for tc in delta.tool_calls:
                    tool_calls.append(
                        ToolCall(
                            id=tc.id or "",
                            name=tc.function.name or "",
                            arguments={},
                        )
                    )
            yield ModelResponse(
                content=content,
                role="assistant",
                tool_calls=tool_calls,
                finish_reason=choice.finish_reason,
                model=self._default_model,
            )

    async def is_available(self) -> bool:
        if not self._client:
            return False
        try:
            await self._client.models.list()
            return True
        except Exception:
            return False

    def _to_openai_messages(
        self, messages: List[ModelMessage]
    ) -> List[ChatCompletionMessageParam]:
        result: List[ChatCompletionMessageParam] = []
        for msg in messages:
            result.append(
                {
                    "role": msg.role,
                    "content": msg.content,
                }
            )
        return result
