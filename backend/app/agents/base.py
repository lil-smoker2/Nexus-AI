"""Base agent interface for NEXUS AI agents."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from enum import Enum


class AgentType(str, Enum):
    COMPANION = "companion"
    CODING = "coding"
    COMPUTER = "computer"
    LIFE_MANAGEMENT = "life_management"


class ExecutionStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    BLOCKED = "blocked"
    FAILED = "failed"


@dataclass
class AgentContext:
    """Context provided to an agent during execution."""

    execution_id: str
    agent_type: AgentType
    conversation_id: Optional[str] = None
    user_id: Optional[str] = None
    messages: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentResult:
    """Result returned by an agent after processing."""

    success: bool
    message: str
    status: ExecutionStatus = ExecutionStatus.COMPLETED
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class BaseAgent(ABC):
    """Abstract base class for all NEXUS AI agents."""

    agent_type: AgentType

    def __init__(self, agent_type: AgentType):
        self.agent_type = agent_type

    @abstractmethod
    async def execute(self, context: AgentContext) -> AgentResult:
        """Execute the agent's logic for the given context."""
        raise NotImplementedError

    async def can_handle(self, message: str, context: Optional[Dict[str, Any]] = None) -> float:
        """Return a confidence score (0.0-1.0) indicating whether this agent can handle the message."""
        return 0.0
