"""Companion agent: handles conversational messages via the model service."""

from typing import Any, Dict, List, Optional

from app.agents.base import (
    AgentContext,
    AgentResult,
    AgentType,
    BaseAgent,
    ExecutionStatus,
)
from app.services.model_service import model_service
from app.models.schemas import GenerationRequest


class CompanionAgent(BaseAgent):
    """Conversational companion agent. Default handler for chat messages."""

    agent_type = AgentType.COMPANION

    def __init__(self):
        super().__init__(AgentType.COMPANION)

    async def execute(self, context: AgentContext) -> AgentResult:
        messages: List[Dict[str, Any]] = [
            {
                "role": "system",
                "content": (
                    "You are NEXUS AI, a helpful personal assistant and conversational companion. "
                    "Be concise, natural, and supportive."
                ),
            }
        ]
        messages.extend(context.messages)

        try:
            response = await model_service.generate(
                GenerationRequest(
                    messages=messages,
                    temperature=0.7,
                )
            )
            return AgentResult(
                success=True,
                message=response.content,
                status=ExecutionStatus.COMPLETED,
                metadata={"model": response.model, "usage": response.usage},
            )
        except Exception as exc:
            return AgentResult(
                success=False,
                message=f"Companion failed to generate response: {exc}",
                status=ExecutionStatus.FAILED,
                errors=[str(exc)],
            )

    async def can_handle(self, message: str, context: Optional[Dict[str, Any]] = None) -> float:
        # Default/fallback agent: always capable at low baseline
        return 0.5
