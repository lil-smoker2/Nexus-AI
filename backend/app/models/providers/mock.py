"""Mock/local model provider for testing and development.

Returns deterministic responses based on input keywords. Always available,
requires no external model files or API keys. Suitable for validating the
model integration layer end-to-end before connecting a real inference backend.
"""

import asyncio
import re
from typing import Any, AsyncIterator, Dict, List, Optional

from app.models.providers.base import (
    GenerationConfig,
    ModelInfo,
    ModelMessage,
    ModelProvider,
    ModelProviderError,
    ModelResponse,
    ToolCall,
)


class MockModelProvider(ModelProvider):
    """A deterministic mock model provider.

    Response selection is based on keyword matching in the user's last message.
    Useful for end-to-end testing of the chat pipeline without a real model.
    """

    RESPONSES = [
        "I understand you said: '{input}'. How can I help you further?",
        "That's interesting. Could you tell me more about '{input}'?",
        "I've received your message about '{input}'. What would you like to do next?",
        "Thanks for sharing '{input}'. I'm here to help with whatever you need.",
        "I hear you mentioning '{input}'. Is there something specific you'd like me to assist with?",
    ]

    FALLBACK_RESPONSE = "I'm here and ready to help. What's on your mind?"

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__("mock", config)
        self._models = [
            ModelInfo(
                id="mock-local",
                name="Mock Local Model",
                provider="mock",
                context_window=4096,
                supports_streaming=True,
                supports_tools=False,
                supports_structured_output=False,
                is_local=True,
                is_available=True,
            )
        ]
        self._active_model = "mock-local"

    async def initialize(self) -> None:
        await asyncio.sleep(0.1)  # simulate model load
        self._initialized = True

    async def list_models(self) -> List[ModelInfo]:
        return self._models

    async def generate(
        self,
        messages: List[ModelMessage],
        config: Optional[GenerationConfig] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> ModelResponse:
        if not self._initialized:
            raise ModelProviderError("Mock provider not initialized")

        user_content = ""
        for msg in reversed(messages):
            if msg.role == "user":
                user_content = msg.content
                break

        response_text = self._select_response(user_content)
        usage = {
            "prompt_tokens": len(user_content.split()),
            "completion_tokens": len(response_text.split()),
            "total_tokens": len(user_content.split()) + len(response_text.split()),
        }

        return ModelResponse(
            content=response_text,
            role="assistant",
            finish_reason="stop",
            usage=usage,
            model=self._active_model,
        )

    async def stream(
        self,
        messages: List[ModelMessage],
        config: Optional[GenerationConfig] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> AsyncIterator[ModelResponse]:
        response = await self.generate(messages, config, tools)
        words = response.content.split()
        for i, word in enumerate(words):
            chunk = ModelResponse(
                content=word + (" " if i < len(words) - 1 else ""),
                role="assistant",
                finish_reason=None,
                model=self._active_model,
            )
            yield chunk
            await asyncio.sleep(0.02)
        final = ModelResponse(
            content="",
            role="assistant",
            finish_reason="stop",
            usage=response.usage,
            model=self._active_model,
        )
        yield final

    async def is_available(self) -> bool:
        return True

    def _select_response(self, user_content: str) -> str:
        if not user_content.strip():
            return self.FALLBACK_RESPONSE
        idx = abs(hash(user_content)) % len(self.RESPONSES)
        return self.RESPONSES[idx].format(input=user_content[:60])
