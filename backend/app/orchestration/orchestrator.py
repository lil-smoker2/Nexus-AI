"""Orchestrator: routes messages to the appropriate agent."""

from typing import Dict, Optional

from app.agents.base import AgentContext, AgentResult, AgentType, BaseAgent
from app.agents.companion.agent import CompanionAgent


class Orchestrator:
    """Simple orchestrator that routes to agents based on intent/confidence.

    For now, all conversational messages go to the Companion agent.
    Later: intent classification, routing to coding/computer/life agents.
    """

    def __init__(self):
        self._agents: Dict[AgentType, BaseAgent] = {
            AgentType.COMPANION: CompanionAgent(),
        }

    def get_agent(self, agent_type: AgentType) -> Optional[BaseAgent]:
        return self._agents.get(agent_type)

    async def route(self, context: AgentContext) -> AgentResult:
        """Route the context to the best agent and execute it."""
        agent = self._agents.get(context.agent_type) or self._agents[AgentType.COMPANION]
        return await agent.execute(context)


orchestrator = Orchestrator()
