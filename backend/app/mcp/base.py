"""Base classes and data models for MCP servers and tools."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


@dataclass
class ToolDefinition:
    name: str
    description: str
    input_schema: Dict[str, Any]
    permission: str = "read"  # read/write/execute/destructive


@dataclass
class ToolResult:
    success: bool
    content: Any = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class McpServerConfig:
    id: str
    name: str
    description: str = ""
    transport: str = "internal"  # internal/stdio/streamable_http (internal implemented)
    endpoint: str = ""
    args: List[Any] = field(default_factory=list)
    env: Dict[str, Any] = field(default_factory=dict)
    auth_config: Dict[str, Any] = field(default_factory=dict)
    permissions: Dict[str, Any] = field(default_factory=dict)
    timeout_ms: int = 30000


class BaseMcpServer:
    """Base class for an MCP server implementation."""

    server_type: str = "base"

    def __init__(self, config: McpServerConfig):
        self.config = config
        self.connected = False
        self._tools: Dict[str, ToolDefinition] = {}
        self._handlers: Dict[str, Callable[[Dict[str, Any]], ToolResult]] = {}

    def initialize(self) -> Dict[str, Any]:
        self.connected = True
        return {
            "protocol": "mcp-internal/0.1",
            "server": {"id": self.config.id, "name": self.config.name, "type": self.server_type},
            "capabilities": {"tools": True, "resources": False, "prompts": False},
        }

    def connect(self) -> None:
        self.initialize()

    def disconnect(self) -> None:
        self.connected = False

    def list_tools(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": t.name,
                "description": t.description,
                "inputSchema": t.input_schema,
                "permission": t.permission,
            }
            for t in self._tools.values()
        ]

    def register_tool(self, definition: ToolDefinition, handler: Callable[[Dict[str, Any]], ToolResult]) -> None:
        self._tools[definition.name] = definition
        self._handlers[definition.name] = handler

    def call_tool(self, name: str, arguments: Dict[str, Any]) -> ToolResult:
        if not self.connected:
            return ToolResult(success=False, error="Server not connected")
        tool = self._tools.get(name)
        handler = self._handlers.get(name)
        if not tool or not handler:
            return ToolResult(success=False, error=f"Unknown tool: {name}")
        start = time.time()
        try:
            result = handler(arguments or {})
        except Exception as exc:  # pragma: no cover - defensive
            result = ToolResult(success=False, error=str(exc))
        result.metadata.setdefault("tool", name)
        result.metadata.setdefault("duration_ms", int((time.time() - start) * 1000))
        return result

    def health(self) -> Dict[str, Any]:
        return {"connected": self.connected, "tools": len(self._tools)}

    def close(self) -> None:
        self.disconnect()
