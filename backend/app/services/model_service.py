"""Model management service.

Manages provider lifecycle, model selection, and generation routing.
Providers are registered by name; one model is active at a time.
"""

import asyncio
from typing import Any, Dict, List, Optional

from app.core.config import settings
from app.models.providers.base import (
    GenerationConfig,
    ModelInfo,
    ModelMessage,
    ModelProvider,
    ModelProviderError,
    ModelResponse,
)
from app.models.providers.mock import MockModelProvider
from app.models.providers.openai import OpenAICompatibleProvider
from app.models.schemas import (
    GenerationRequest,
    GenerationResponse,
    ModelInfo as SchemaModelInfo,
    ModelListResponse,
    ModelSelectRequest,
    ModelSelectResponse,
    ProviderInfo,
    ProvidersResponse,
)


class ModelService:
    """Central service for model provider management and generation."""

    PROVIDER_CLASSES: Dict[str, type[ModelProvider]] = {
        "mock": MockModelProvider,
        "openai-compatible": OpenAICompatibleProvider,
    }

    def __init__(self) -> None:
        self._providers: Dict[str, ModelProvider] = {}
        self._active_model_id: Optional[str] = None
        self._active_provider_name: Optional[str] = None
        self._lock = asyncio.Lock()

    async def initialize(self) -> None:
        """Initialize providers from config (mock + optional local/online OpenAI-compatible)."""
        # Always register mock as fallback
        mock = MockModelProvider()
        await mock.initialize()
        self._providers["mock"] = mock
        self._active_model_id = "mock-local"
        self._active_provider_name = "mock"

        # Local OpenAI-compatible (e.g. Ollama)
        if settings.LOCAL_MODEL_ENABLED:
            local = OpenAICompatibleProvider(
                config={
                    "api_key": settings.LOCAL_MODEL_API_KEY,
                    "base_url": settings.LOCAL_MODEL_BASE_URL,
                    "default_model": settings.LOCAL_MODEL_DEFAULT_MODEL,
                }
            )
            try:
                await local.initialize()
                self._providers["local"] = local
                # Prefer local if available
                if await local.is_available():
                    self._active_model_id = settings.LOCAL_MODEL_DEFAULT_MODEL
                    self._active_provider_name = "local"
            except Exception:
                pass

        # Online/OpenAI-compatible cloud
        if settings.ONLINE_MODEL_ENABLED and (settings.OPENAI_API_KEY or settings.OPENAI_BASE_URL):
            cloud_cfg: Dict[str, Any] = {
                "api_key": settings.OPENAI_API_KEY or None,
                "default_model": settings.OPENAI_DEFAULT_MODEL,
            }
            if settings.OPENAI_BASE_URL:
                cloud_cfg["base_url"] = settings.OPENAI_BASE_URL
            cloud = OpenAICompatibleProvider(config=cloud_cfg)
            try:
                await cloud.initialize()
                self._providers["openai"] = cloud
                # Prefer online if no local picked and online is available
                if not settings.LOCAL_MODEL_ENABLED or self._active_provider_name == "mock":
                    if await cloud.is_available():
                        self._active_model_id = settings.OPENAI_DEFAULT_MODEL
                        self._active_provider_name = "openai"
            except Exception:
                pass

    async def shutdown(self) -> None:
        """Shut down all providers."""
        for provider in self._providers.values():
            try:
                await provider.shutdown()
            except Exception:
                pass
        self._providers.clear()
        self._active_model_id = None
        self._active_provider_name = None

    def register_provider(
        self, name: str, provider: ModelProvider
    ) -> None:
        """Register a provider instance by name."""
        self._providers[name] = provider

    def get_provider(self, name: str) -> Optional[ModelProvider]:
        return self._providers.get(name)

    def get_active_provider(self) -> Optional[ModelProvider]:
        if self._active_provider_name:
            return self._providers.get(self._active_provider_name)
        return None

    def get_active_model_id(self) -> Optional[str]:
        return self._active_model_id


    async def list_providers(self) -> ProvidersResponse:
        """List all registered providers with availability and models."""
        provider_infos: List[ProviderInfo] = []
        for name, provider in self._providers.items():
            available = await provider.is_available()
            models: List[str] = []
            if available:
                try:
                    model_infos = await provider.list_models()
                    models = [m.id for m in model_infos]
                except Exception:
                    models = []
            provider_infos.append(
                ProviderInfo(
                    name=name,
                    type="local" if name == "mock" else "cloud",
                    is_available=available,
                    models=models,
                )
            )
        return ProvidersResponse(providers=provider_infos)

    async def list_models(self) -> ModelListResponse:
        """List all models across all providers."""
        all_models: List[SchemaModelInfo] = []
        for provider in self._providers.values():
            try:
                model_infos = await provider.list_models()
                for mi in model_infos:
                    all_models.append(
                        SchemaModelInfo(
                            id=mi.id,
                            name=mi.name,
                            provider=mi.provider,
                            context_window=mi.context_window,
                            supports_streaming=mi.supports_streaming,
                            supports_tools=mi.supports_tools,
                            supports_structured_output=mi.supports_structured_output,
                            is_local=mi.is_local,
                            is_available=mi.is_available,
                            metadata=mi.metadata,
                        )
                    )
            except Exception:
                pass
        return ModelListResponse(
            models=all_models,
            active_model=self._active_model_id,
        )

    async def select_model(self, request: ModelSelectRequest) -> ModelSelectResponse:
        """Select a model to use for generation.

        Finds the provider that offers the given model_id and sets it active.
        """
        target_provider: Optional[ModelProvider] = None
        target_provider_name: Optional[str] = None
        target_model: Optional[ModelInfo] = None

        for name, provider in self._providers.items():
            try:
                models = await provider.list_models()
                for mi in models:
                    if mi.id == request.model_id:
                        target_provider = provider
                        target_provider_name = name
                        target_model = mi
                        break
            except Exception:
                continue
            if target_provider:
                break

        if not target_provider or not target_model:
            raise ModelProviderError(
                f"Model '{request.model_id}' not found in any registered provider"
            )

        if not await target_provider.is_available():
            try:
                await target_provider.initialize()
            except Exception as exc:
                raise ModelProviderError(
                    f"Failed to initialize provider for model '{request.model_id}': {exc}"
                ) from exc

        self._active_provider_name = target_provider_name
        self._active_model_id = request.model_id

        return ModelSelectResponse(
            model_id=request.model_id,
            provider=target_provider_name or "unknown",
            status="selected",
        )

    async def generate(
        self, request: GenerationRequest
    ) -> GenerationResponse:
        """Generate a response using the active provider.

        If request.model_id is given, switches to that model first.
        """
        provider = self.get_active_provider()
        if not provider:
            raise ModelProviderError("No model provider is active")

        if request.model_id and request.model_id != self._active_model_id:
            await self.select_model(ModelSelectRequest(model_id=request.model_id))
            provider = self.get_active_provider()
            if not provider:
                raise ModelProviderError(
                    f"Failed to switch to model '{request.model_id}'"
                )

        messages = [
            ModelMessage(
                role=m.get("role", "user"),
                content=m.get("content", ""),
            )
            for m in request.messages
        ]

        config = GenerationConfig(
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            stream=request.stream,
        )

        response: ModelResponse = await provider.generate(messages, config)

        return GenerationResponse(
            content=response.content,
            role=response.role,
            model=response.model or self._active_model_id or "unknown",
            finish_reason=response.finish_reason,
            usage=response.usage,
        )

    async def stream_generate(
        self, request: GenerationRequest
    ):
        """Stream a response using the active provider."""
        provider = self.get_active_provider()
        if not provider:
            raise ModelProviderError("No model provider is active")

        if request.model_id and request.model_id != self._active_model_id:
            await self.select_model(ModelSelectRequest(model_id=request.model_id))
            provider = self.get_active_provider()

        messages = [
            ModelMessage(
                role=m.get("role", "user"),
                content=m.get("content", ""),
            )
            for m in request.messages
        ]

        config = GenerationConfig(
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            stream=True,
        )

        async for chunk in provider.stream(messages, config):
            yield chunk


model_service = ModelService()
