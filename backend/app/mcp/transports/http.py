"""Streamable HTTP MCP client (basic JSON-RPC over HTTP POST)."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from app.mcp.protocol import (
    DEFAULT_PROTOCOL_VERSION,
    McpCapabilities,
    NormalizedToolResult,
    new_id,
    notification,
    request,
)


class HttpMcpError(Exception):
    pass


class HttpMcpClient:
    """Minimal HTTP MCP client.

    Supports JSON-RPC request/response via POST. MCP Streamable HTTP may use SSE
    for server->client messages; this client handles basic request/response flows
    sufficient for tool discovery and invocation on compatible endpoints.
    """

    def __init__(
        self,
        endpoint: str,
        headers: Optional[Dict[str, str]] = None,
        timeout_ms: int = 30000,
        client_name: str = "nexus-ai",
        client_version: str = "0.1.0",
    ):
        self.endpoint = endpoint
        self.headers = {"Content-Type": "application/json", "Accept": "application/json", **(headers or {})}
        self.timeout_ms = timeout_ms
        self.client_name = client_name
        self.client_version = client_version

        self.connected = False
        self.initialize_result: Dict[str, Any] = {}
        self.capabilities = McpCapabilities()
        self.server_info: Dict[str, Any] = {}
        self.protocol_version: Optional[str] = None
        self.session_id: Optional[str] = None

    def _post(self, payload: Dict[str, Any], timeout_ms: Optional[int] = None) -> Dict[str, Any]:
        try:
            import httpx
        except Exception as e:
            raise HttpMcpError("httpx is required for HTTP MCP transport") from e
        timeout = (timeout_ms if timeout_ms is not None else self.timeout_ms) / 1000.0
        headers = dict(self.headers)
        if self.session_id:
            headers["Mcp-Session-Id"] = self.session_id
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            resp = client.post(self.endpoint, json=payload, headers=headers)
        # capture session id if provided
        sid = resp.headers.get("Mcp-Session-Id") or resp.headers.get("mcp-session-id")
        if sid:
            self.session_id = sid
        content_type = (resp.headers.get("content-type") or "").lower()
        body: Any = None
        if "application/json" in content_type or resp.text.strip().startswith("{"):
            try:
                body = resp.json()
            except Exception:
                body = None
        elif "text/event-stream" in content_type:
            # parse simple SSE for a JSON-RPC response event
            body = self._parse_sse_response(resp.text)
        if resp.status_code >= 400 and body is None:
            raise HttpMcpError(f"HTTP {resp.status_code}: {resp.text[:500]}")
        if not isinstance(body, dict):
            raise HttpMcpError(f"Unexpected HTTP MCP response: {resp.text[:500]}")
        return body

    def _parse_sse_response(self, text: str) -> Optional[Dict[str, Any]]:
        # look for `data: {json}` lines and return first JSON-RPC response
        last_obj = None
        for line in text.splitlines():
            line = line.strip()
            if not line.startswith("data:"):
                continue
            data = line[len("data:"):].strip()
            if not data or data == "[DONE]":
                continue
            try:
                obj = json.loads(data)
                if isinstance(obj, dict):
                    last_obj = obj
                    if "result" in obj or "error" in obj:
                        return obj
            except Exception:
                continue
        return last_obj

    def request(self, method: str, params: Optional[Dict[str, Any]] = None, timeout_ms: Optional[int] = None) -> Dict[str, Any]:
        msg = request(method, params=params, req_id=new_id())
        resp = self._post(msg, timeout_ms=timeout_ms)
        if "error" in resp and resp.get("error"):
            err = resp.get("error") or {}
            raise HttpMcpError(err.get("message") or str(err))
        return resp.get("result") or {}

    def notify(self, method: str, params: Optional[Dict[str, Any]] = None) -> None:
        # best-effort notification
        msg = notification(method, params=params)
        try:
            self._post(msg)
        except Exception:
            pass

    def initialize(self) -> Dict[str, Any]:
        params = {
            "protocolVersion": DEFAULT_PROTOCOL_VERSION,
            "capabilities": {},
            "clientInfo": {"name": self.client_name, "version": self.client_version},
        }
        result = self.request("initialize", params=params)
        self.initialize_result = result or {}
        self.capabilities = McpCapabilities.from_result(self.initialize_result)
        self.server_info = (self.initialize_result or {}).get("serverInfo") or {}
        self.protocol_version = (self.initialize_result or {}).get("protocolVersion")
        try:
            self.notify("notifications/initialized", {})
        except Exception:
            pass
        self.connected = True
        return self.initialize_result

    def list_tools(self) -> List[Dict[str, Any]]:
        result = self.request("tools/list", params={})
        tools = (result or {}).get("tools") or []
        return tools if isinstance(tools, list) else []

    def list_resources(self) -> List[Dict[str, Any]]:
        try:
            result = self.request("resources/list", params={})
            resources = (result or {}).get("resources") or []
            return resources if isinstance(resources, list) else []
        except Exception:
            return []

    def list_prompts(self) -> List[Dict[str, Any]]:
        try:
            result = self.request("prompts/list", params={})
            prompts = (result or {}).get("prompts") or []
            return prompts if isinstance(prompts, list) else []
        except Exception:
            return []

    def call_tool(self, name: str, arguments: Optional[Dict[str, Any]] = None, timeout_ms: Optional[int] = None) -> NormalizedToolResult:
        result = self.request("tools/call", params={"name": name, "arguments": arguments or {}}, timeout_ms=timeout_ms)
        return NormalizedToolResult.from_mcp(result if isinstance(result, dict) else {"content": result})

    def health(self) -> Dict[str, Any]:
        return {"connected": self.connected, "endpoint": self.endpoint, "session_id": self.session_id}

    def close(self) -> None:
        self.connected = False
        self.session_id = None
