"""MCP client/manager: registry, connection lifecycle, discovery, and invocation."""

from __future__ import annotations

import os
import time
from typing import Any, Dict, List, Optional

from app.mcp.base import BaseMcpServer, McpServerConfig, ToolResult
from app.mcp.servers import SERVER_CLASSES
from app.database.session import SessionLocal
from app.database.repositories.container import Repositories


def _default_root() -> str:
    # workspace root (repo) - two levels up from backend/app/mcp
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))


DEFAULT_SERVERS = [
    {"name": "filesystem", "server_type": "filesystem", "description": "File and directory operations", "transport": "internal", "endpoint": "filesystem", "args": [_default_root()], "permissions": {"allow": ["read", "write", "destructive"]}},
    {"name": "terminal", "server_type": "terminal", "description": "Command execution", "transport": "internal", "endpoint": "terminal", "args": [_default_root()], "permissions": {"allow": ["read", "execute"]}},
    {"name": "git", "server_type": "git", "description": "Git repository operations", "transport": "internal", "endpoint": "git", "args": [_default_root()], "permissions": {"allow": ["read"]}},
    {"name": "database", "server_type": "database", "description": "Database inspection and read-only queries", "transport": "internal", "endpoint": "database", "args": [_default_root()], "permissions": {"allow": ["read"]}},
    {"name": "browser", "server_type": "browser", "description": "Web fetch/navigation primitives", "transport": "internal", "endpoint": "browser", "args": [], "permissions": {"allow": ["read"]}},
    {"name": "computer", "server_type": "computer", "description": "Desktop/session inspection and controlled actions", "transport": "internal", "endpoint": "computer", "args": [], "permissions": {"allow": ["read", "execute"]}},
    {"name": "task_memory", "server_type": "task_memory", "description": "Task and memory operations", "transport": "internal", "endpoint": "task_memory", "args": [], "permissions": {"allow": ["read", "write", "destructive"]}},
]


class McpManager:
    def __init__(self) -> None:
        self._servers: Dict[str, BaseMcpServer] = {}  # by server id
        self._name_index: Dict[str, str] = {}  # name/type -> id
        self._initialized = False
        self._audit: List[Dict[str, Any]] = []

    def _db(self):
        db = SessionLocal()
        return db, Repositories(db)

    def ensure_defaults(self) -> None:
        db, repos = self._db()
        try:
            for spec in DEFAULT_SERVERS:
                existing = repos.mcp_servers.get_by_name(spec["name"])
                if not existing:
                    repos.mcp_servers.create({
                        "name": spec["name"],
                        "description": spec.get("description", ""),
                        "transport": spec.get("transport", "internal"),
                        "endpoint": spec.get("endpoint", spec["name"]),
                        "args": spec.get("args", []),
                        "env": spec.get("env", {}),
                        "auth_config": {},
                        "connection_state": "disconnected",
                        "discovered_tools": [],
                        "permissions": spec.get("permissions", {}),
                    })
            db.commit()
        finally:
            db.close()

    def initialize(self) -> None:
        self.ensure_defaults()
        self._initialized = True
        # auto-connect internal servers
        servers = self.list_servers()
        for s in servers:
            if s.get("transport") == "internal":
                try:
                    self.connect(s["id"])
                except Exception:
                    pass

    def shutdown(self) -> None:
        for srv in list(self._servers.values()):
            try:
                srv.close()
            except Exception:
                pass
        self._servers.clear()
        self._name_index.clear()

    def _server_type_for(self, record) -> str:
        # endpoint doubles as type for internal servers; fallback to name
        return (record.endpoint or record.name or "").lower()

    def _build_instance(self, record) -> Optional[BaseMcpServer]:
        stype = self._server_type_for(record)
        cls = SERVER_CLASSES.get(stype)
        if not cls:
            return None
        cfg = McpServerConfig(
            id=record.id,
            name=record.name,
            description=record.description or "",
            transport=record.transport or "internal",
            endpoint=record.endpoint or stype,
            args=record.args or [],
            env=record.env or {},
            auth_config=record.auth_config or {},
            permissions=record.permissions or {},
        )
        return cls(cfg)

    def list_servers(self) -> List[Dict[str, Any]]:
        db, repos = self._db()
        try:
            rows = repos.mcp_servers.get_multi(limit=200)
            out = []
            for r in rows:
                inst = self._servers.get(r.id)
                tools = inst.list_tools() if inst and inst.connected else (r.discovered_tools or [])
                out.append({
                    "id": r.id,
                    "name": r.name,
                    "description": r.description,
                    "transport": r.transport,
                    "endpoint": r.endpoint,
                    "args": r.args or [],
                    "status": "connected" if (inst and inst.connected) else (r.connection_state or "disconnected"),
                    "tools_count": len(tools),
                    "discovered_tools": tools,
                    "permissions": r.permissions or {},
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                    "updated_at": r.updated_at.isoformat() if r.updated_at else None,
                })
            return out
        finally:
            db.close()

    def get_server(self, server_id: str) -> Optional[Dict[str, Any]]:
        for s in self.list_servers():
            if s["id"] == server_id:
                return s
        return None

    def _record_update(self, server_id: str, **fields: Any) -> None:
        db, repos = self._db()
        try:
            repos.mcp_servers.update(server_id, fields)
            db.commit()
        finally:
            db.close()

    def connect(self, server_id: str) -> Dict[str, Any]:
        db, repos = self._db()
        try:
            record = repos.mcp_servers.get(server_id)
            if not record:
                raise ValueError("Server not found")
            inst = self._servers.get(server_id)
            if not inst:
                inst = self._build_instance(record)
                if not inst:
                    self._record_update(server_id, connection_state="error")
                    raise ValueError(f"Unsupported MCP server type/transport: {record.endpoint}/{record.transport}")
                self._servers[server_id] = inst
                self._name_index[record.name] = server_id
            init_info = inst.initialize()
            tools = inst.list_tools()
            repos.mcp_servers.update(server_id, {"connection_state": "connected", "discovered_tools": tools})
            db.commit()
            return {"server_id": server_id, "status": "connected", "initialize": init_info, "tools": tools}
        except Exception:
            try:
                repos.mcp_servers.update(server_id, {"connection_state": "error"})
                db.commit()
            except Exception:
                pass
            raise
        finally:
            db.close()

    def disconnect(self, server_id: str) -> Dict[str, Any]:
        inst = self._servers.get(server_id)
        if inst:
            try:
                inst.disconnect()
            except Exception:
                pass
        self._record_update(server_id, connection_state="disconnected")
        return {"server_id": server_id, "status": "disconnected"}

    def call_tool(self, server_id: str, tool_name: str, arguments: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if server_id not in self._servers or not self._servers[server_id].connected:
            self.connect(server_id)
        inst = self._servers[server_id]
        start = time.time()
        result = inst.call_tool(tool_name, arguments or {})
        payload = {
            "server_id": server_id, "server_name": inst.config.name, "tool": tool_name,
            "arguments": arguments or {}, "success": result.success,
            "content": result.content, "error": result.error,
            "metadata": result.metadata, "duration_ms": int((time.time() - start) * 1000),
        }
        self._audit.append({"ts": time.time(), **{k: payload[k] for k in ("server_id","server_name","tool","success","error","duration_ms")}})
        if len(self._audit) > 500:
            self._audit = self._audit[-500:]
        return payload

    def list_tools(self, server_id: Optional[str] = None) -> List[Dict[str, Any]]:
        if server_id:
            s = self.get_server(server_id)
            return s.get("discovered_tools", []) if s else []
        tools = []
        for s in self.list_servers():
            for t in s.get("discovered_tools", []):
                tools.append({"server_id": s["id"], "server_name": s["name"], **t})
        return tools

    def audit_log(self, limit: int = 100) -> List[Dict[str, Any]]:
        return list(reversed(self._audit[-limit:]))


mcp_manager = McpManager()
