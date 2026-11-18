"""MCP JSON-RPC protocol helpers (client side)."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

JSONRPC_VERSION = "2.0"
DEFAULT_PROTOCOL_VERSION = "2024-11-05"


def new_id() -> str:
    return str(uuid.uuid4())


def request(method: str, params: Optional[Dict[str, Any]] = None, req_id: Any = None) -> Dict[str, Any]:
    msg: Dict[str, Any] = {"jsonrpc": JSONRPC_VERSION, "id": req_id if req_id is not None else new_id(), "method": method}
    if params is not None:
        msg["params"] = params
    return msg


def notification(method: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    msg: Dict[str, Any] = {"jsonrpc": JSONRPC_VERSION, "method": method}
    if params is not None:
        msg["params"] = params
    return msg


def error_response(req_id: Any, code: int, message: str, data: Any = None) -> Dict[str, Any]:
    err = {"code": code, "message": message}
    if data is not None:
        err["data"] = data
    return {"jsonrpc": JSONRPC_VERSION, "id": req_id, "error": err}


def encode_message(msg: Dict[str, Any]) -> bytes:
    return (json.dumps(msg, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")


def decode_message(line: str) -> Optional[Dict[str, Any]]:
    line = line.strip()
    if not line:
        return None
    try:
        obj = json.loads(line)
        if isinstance(obj, dict):
            return obj
    except Exception:
        return None
    return None


@dataclass
class McpCapabilities:
    tools: bool = False
    resources: bool = False
    prompts: bool = False
    raw: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_result(cls, result: Dict[str, Any]) -> "McpCapabilities":
        caps = (result or {}).get("capabilities") or {}
        def has(name: str) -> bool:
            v = caps.get(name)
            return bool(v) or isinstance(v, dict)
        return cls(tools=has("tools"), resources=has("resources"), prompts=has("prompts"), raw=caps)


@dataclass
class NormalizedToolResult:
    success: bool
    content: Any = None
    error: Optional[str] = None
    is_error: bool = False
    raw: Any = None

    @classmethod
    def from_mcp(cls, result: Dict[str, Any]) -> "NormalizedToolResult":
        # MCP tools/call result: {content:[{type,text|...}], isError?:bool, structuredContent?:...}
        if not isinstance(result, dict):
            return cls(success=True, content=result, raw=result)
        is_error = bool(result.get("isError"))
        content = result.get("content")
        structured = result.get("structuredContent")
        text_parts: List[str] = []
        if isinstance(content, list):
            for item in content:
                if isinstance(item, dict):
                    if item.get("type") == "text" and "text" in item:
                        text_parts.append(str(item.get("text", "")))
                    elif "text" in item:
                        text_parts.append(str(item.get("text", "")))
        text = "\n".join([t for t in text_parts if t]) if text_parts else None
        payload = structured if structured is not None else (text if text is not None else content)
        err = None
        if is_error:
            err = text or (str(structured) if structured is not None else "Tool returned error")
        return cls(success=not is_error, content=payload, error=err, is_error=is_error, raw=result)
