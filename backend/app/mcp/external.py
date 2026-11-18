"""External MCP server client adapter (stdio / streamable HTTP)."""

from __future__ import annotations

import time
from typing import Any, Callable, Dict, List, Optional

from app.mcp.base import BaseMcpServer, McpServerConfig, ToolDefinition, ToolResult
from app.mcp.transports.stdio import StdioMcpClient, StdioMcpError
from app.mcp.transports.http import HttpMcpClient, HttpMcpError


class ExternalMcpServer(BaseMcpServer):
    """Adapter that exposes an external MCP process/endpoint via BaseMcpServer API."""

    server_type = "external"

    def __init__(self, config: McpServerConfig):
        super().__init__(config)
        self.transport_kind = (config.transport or "").lower()
        self.client: Any = None
        self.resources: List[Dict[str, Any]] = []
        self.prompts: List[Dict[str, Any]] = []
        self._tool_meta: Dict[str, Dict[str, Any]] = {}

    def _build_client(self):
        cfg = self.config.config or {}
        timeout_ms = int(cfg.get("timeout_ms") or self.config.timeout_ms or 30000)
        if self.transport_kind == "stdio":
            cmd = self.config.endpoint
            args = self.config.args or []
            env = self.config.env or {}
            cwd = cfg.get("cwd")
            return StdioMcpClient(command=cmd, args=list(args), env=dict(env), cwd=cwd, timeout_ms=timeout_ms)
        if self.transport_kind in ("streamable_http", "http"):
            headers = dict((self.config.auth_config or {}).get("headers") or {})
            # allow auth token helper
            token = (self.config.auth_config or {}).get("token") or (self.config.auth_config or {}).get("bearer_token")
            if token and "Authorization" not in headers:
                headers["Authorization"] = f"Bearer {token}"
            headers.update(dict(cfg.get("headers") or {}))
            return HttpMcpClient(endpoint=self.config.endpoint, headers=headers, timeout_ms=timeout_ms)
        raise ValueError(f"Unsupported external transport: {self.transport_kind}")

    def initialize(self) -> Dict[str, Any]:
        self.client = self._build_client()
        init_result = self.client.initialize()
        self.connected = True
        self._tools.clear()
        self._handlers.clear()
        self._tool_meta.clear()
        self.resources = []
        self.prompts = []

        try:
            tools = self.client.list_tools() or []
        except Exception:
            tools = []
        for t in tools:
            if not isinstance(t, dict):
                continue
            name = str(t.get("name") or "").strip()
            if not name:
                continue
            desc = str(t.get("description") or "")
            schema = t.get("inputSchema") or t.get("input_schema") or {"type": "object", "properties": {}}
            # heuristic permission by name
            lname = name.lower()
            perm = "read"
            if any(k in lname for k in ["delete", "remove", "drop", "kill", "destroy", "rm", "purge", "clear", "reset", "uninstall"]):
                perm = "destructive"
            elif any(k in lname for k in [
                "write", "create", "update", "edit", "set", "put", "post", "patch", "move", "copy", "install",
                "exec", "run", "commit", "push", "add", "append", "insert", "store", "save", "send", "upload",
                "modify", "rename", "notify", "open", "launch", "start", "stop", "restart", "toggle", "enable",
                "disable", "apply", "merge", "publish", "record", "register", "import", "export",
            ]):
                perm = "write"
            td = ToolDefinition(name=name, description=desc, input_schema=schema, permission=perm)
            self._tools[name] = td
            self._tool_meta[name] = t
            self._handlers[name] = self._make_handler(name)

        try:
            self.resources = self.client.list_resources() or []
        except Exception:
            self.resources = []
        try:
            self.prompts = self.client.list_prompts() or []
        except Exception:
            self.prompts = []

        caps = getattr(self.client, "capabilities", None)
        capabilities = {
            "tools": bool(getattr(caps, "tools", False) or self._tools),
            "resources": bool(getattr(caps, "resources", False) or self.resources),
            "prompts": bool(getattr(caps, "prompts", False) or self.prompts),
            "raw": getattr(caps, "raw", {}) if caps else {},
        }
        return {
            "protocol": getattr(self.client, "protocol_version", None) or "mcp",
            "server": {"id": self.config.id, "name": self.config.name, "type": self.transport_kind, "info": getattr(self.client, "server_info", {})},
            "capabilities": capabilities,
            "resources": self.resources,
            "prompts": self.prompts,
        }

    def _make_handler(self, name: str) -> Callable[[Dict[str, Any]], ToolResult]:
        def handler(arguments: Dict[str, Any]) -> ToolResult:
            if not self.client:
                return ToolResult(success=False, error="External client not initialized")
            start = time.time()
            try:
                timeout_ms = int((self.config.config or {}).get("tool_timeout_ms") or self.config.timeout_ms or 30000)
                norm = self.client.call_tool(name, arguments or {}, timeout_ms=timeout_ms)
                return ToolResult(
                    success=bool(norm.success),
                    content=norm.content,
                    error=norm.error,
                    metadata={"tool": name, "duration_ms": int((time.time() - start) * 1000), "raw": norm.raw, "is_error": norm.is_error},
                )
            except (StdioMcpError, HttpMcpError) as e:
                return ToolResult(success=False, error=str(e), metadata={"tool": name})
            except Exception as e:
                return ToolResult(success=False, error=str(e), metadata={"tool": name})
        return handler

    def list_tools(self) -> List[Dict[str, Any]]:
        items = super().list_tools()
        # enrich with source
        for it in items:
            meta = self._tool_meta.get(it.get("name"))
            if meta:
                it["source"] = "external"
        return items

    def list_resources(self) -> List[Dict[str, Any]]:
        return list(self.resources or [])

    def list_prompts(self) -> List[Dict[str, Any]]:
        return list(self.prompts or [])

    def disconnect(self) -> None:
        try:
            if self.client and hasattr(self.client, "close"):
                self.client.close()
        finally:
            self.client = None
            self.connected = False

    def health(self) -> Dict[str, Any]:
        h = {"connected": self.connected, "transport": self.transport_kind}
        if self.client and hasattr(self.client, "health"):
            try:
                h.update(self.client.health() or {})
            except Exception:
                pass
        return h
