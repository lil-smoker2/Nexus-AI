"""MCP client/manager: registry, connection lifecycle, discovery, invocation, security, audit."""

from __future__ import annotations

import copy
import os
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from app.mcp.base import BaseMcpServer, McpServerConfig, ToolResult
from app.mcp.servers import SERVER_CLASSES
from app.mcp.external import ExternalMcpServer
from app.database.session import SessionLocal
from app.database.repositories.container import Repositories


def _default_root() -> str:
    # workspace root (repo) - three levels up from backend/app/mcp/manager.py? actually file is backend/app/mcp/manager.py
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))


DEFAULT_SERVERS = [
    {"name": "filesystem", "server_type": "filesystem", "description": "File and directory operations", "transport": "internal", "endpoint": "filesystem", "args": [_default_root()], "permissions": {"allow": ["read", "write", "destructive"]}, "config": {"root": _default_root()}},
    {"name": "terminal", "server_type": "terminal", "description": "Command execution", "transport": "internal", "endpoint": "terminal", "args": [_default_root()], "permissions": {"allow": ["read", "execute", "write"]}, "config": {"root": _default_root()}},
    {"name": "git", "server_type": "git", "description": "Git repository operations", "transport": "internal", "endpoint": "git", "args": [_default_root()], "permissions": {"allow": ["read", "write"]}, "config": {"root": _default_root(), "allow_mutating": False}},
    {"name": "database", "server_type": "database", "description": "Database inspection and read-only queries", "transport": "internal", "endpoint": "database", "args": [_default_root()], "permissions": {"allow": ["read"]}, "config": {"root": _default_root(), "read_only": True}},
    {"name": "browser", "server_type": "browser", "description": "Web fetch/navigation primitives", "transport": "internal", "endpoint": "browser", "args": [], "permissions": {"allow": ["read"]}, "config": {}},
    {"name": "computer", "server_type": "computer", "description": "Desktop/session inspection and controlled actions", "transport": "internal", "endpoint": "computer", "args": [], "permissions": {"allow": ["read", "execute", "destructive"]}, "config": {"require_approval_for": ["destructive"]}},
    {"name": "task_memory", "server_type": "task_memory", "description": "Task and memory operations", "transport": "internal", "endpoint": "task_memory", "args": [], "permissions": {"allow": ["read", "write", "destructive"]}, "config": {}},
    {"name": "pacman", "server_type": "pacman", "description": "Arch Linux pacman package management (read-only by default; mutating ops disabled)", "transport": "internal", "endpoint": "pacman", "args": [], "permissions": {"allow": ["read", "destructive"]}, "config": {"allow_mutating": False, "require_approval_for": ["destructive"]}},
]

SENSITIVE_KEYS = {"token", "access_token", "refresh_token", "api_key", "apikey", "password", "secret", "client_secret", "authorization", "bearer", "private_key"}


def _redact(obj: Any, depth: int = 0) -> Any:
    if depth > 6:
        return "***"
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            lk = str(k).lower()
            if lk in SENSITIVE_KEYS or any(s in lk for s in ["secret", "token", "password", "key"]):
                out[k] = "***REDACTED***"
            else:
                out[k] = _redact(v, depth + 1)
        return out
    if isinstance(obj, list):
        return [_redact(v, depth + 1) for v in obj[:200]]
    if isinstance(obj, str) and len(obj) > 4000:
        return obj[:4000] + "...<truncated>"
    return obj


class McpManager:
    def __init__(self) -> None:
        self._servers: Dict[str, BaseMcpServer] = {}  # by server id
        self._initialized = False
        self._audit_cache: List[Dict[str, Any]] = []
        self._lockless_warned = False

    # ---- db helpers ----
    def _db(self):
        db = SessionLocal()
        return db, Repositories(db)

    def _to_public_server(self, record, inst: Optional[BaseMcpServer] = None) -> Dict[str, Any]:
        tools = inst.list_tools() if inst and getattr(inst, "connected", False) else (record.discovered_tools or [])
        resources = inst.list_resources() if inst and hasattr(inst, "list_resources") and getattr(inst, "connected", False) else ((record.capabilities or {}).get("resources_list") or [])
        prompts = inst.list_prompts() if inst and hasattr(inst, "list_prompts") and getattr(inst, "connected", False) else ((record.capabilities or {}).get("prompts_list") or [])
        status = "connected" if (inst and getattr(inst, "connected", False)) else (record.connection_state or "disconnected")
        cfg = record.config or {}
        # redact sensitive config/env/auth in public view
        return {
            "id": record.id,
            "name": record.name,
            "description": record.description,
            "transport": record.transport,
            "endpoint": record.endpoint,
            "args": record.args or [],
            "enabled": bool(record.enabled) if record.enabled is not None else True,
            "status": status,
            "connection_state": status,
            "tools_count": len(tools or []),
            "resources_count": len(resources or []),
            "prompts_count": len(prompts or []),
            "discovered_tools": tools or [],
            "resources": resources or [],
            "prompts": prompts or [],
            "permissions": record.permissions or {},
            "config": _redact(cfg),
            "env_keys": sorted(list((record.env or {}).keys())),
            "auth_configured": bool(record.auth_config),
            "server_info": record.server_info or {},
            "capabilities": record.capabilities or {},
            "last_error": record.last_error,
            "last_connected_at": record.last_connected_at.isoformat() if record.last_connected_at else None,
            "created_at": record.created_at.isoformat() if record.created_at else None,
            "updated_at": record.updated_at.isoformat() if record.updated_at else None,
        }

    # ---- registry / defaults ----
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
                        "config": spec.get("config", {}),
                        "enabled": True,
                        "connection_state": "disconnected",
                        "discovered_tools": [],
                        "permissions": spec.get("permissions", {}),
                        "server_info": {},
                        "capabilities": {},
                    })
                else:
                    # backfill missing config/enabled but do not overwrite user changes
                    updates = {}
                    if existing.config is None:
                        updates["config"] = spec.get("config", {})
                    if existing.enabled is None:
                        updates["enabled"] = True
                    if spec["name"] == "computer":
                        perms = existing.permissions or {}
                        cfg = dict(existing.config or {})
                        if perms.get("allow") == ["read", "execute"] and not cfg.get("require_approval_for"):
                            updates["permissions"] = {**perms, "allow": list(spec["permissions"]["allow"])}
                            updates["config"] = {**cfg, **(spec.get("config") or {})}
                    if updates:
                        repos.mcp_servers.update(existing.id, updates)
            db.commit()
        finally:
            db.close()

    def initialize(self) -> None:
        self.ensure_defaults()
        self._initialized = True
        servers = self.list_servers()
        for s in servers:
            if s.get("transport") == "internal" and s.get("enabled", True):
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

    # ---- registry CRUD ----
    def register_server(self, data: Dict[str, Any]) -> Dict[str, Any]:
        name = (data.get("name") or "").strip()
        transport = (data.get("transport") or "").strip().lower()
        endpoint = data.get("endpoint")
        if not name:
            raise ValueError("name is required")
        if transport not in ("internal", "stdio", "streamable_http", "http"):
            raise ValueError("transport must be one of internal, stdio, streamable_http, http")
        if transport == "internal":
            stype = (data.get("server_type") or endpoint or name).lower()
            if stype not in SERVER_CLASSES:
                raise ValueError(f"Unsupported internal server type: {stype}")
            endpoint = endpoint or stype
        else:
            if not endpoint:
                raise ValueError("endpoint is required for external transports")
        db, repos = self._db()
        try:
            if repos.mcp_servers.get_by_name(name):
                raise ValueError(f"Server with name '{name}' already exists")
            rec = repos.mcp_servers.create({
                "name": name,
                "description": data.get("description") or "",
                "transport": transport,
                "endpoint": endpoint,
                "args": data.get("args") or [],
                "env": data.get("env") or {},
                "auth_config": data.get("auth_config") or {},
                "config": data.get("config") or {},
                "enabled": bool(data.get("enabled", True)),
                "connection_state": "disconnected",
                "discovered_tools": [],
                "permissions": data.get("permissions") or {},
                "server_info": {},
                "capabilities": {},
            })
            db.commit()
            return self.get_server(rec.id) or {"id": rec.id, "name": name}
        finally:
            db.close()

    def update_server(self, server_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        allowed = {"name", "description", "transport", "endpoint", "args", "env", "auth_config", "config", "enabled", "permissions"}
        updates = {k: v for k, v in data.items() if k in allowed}
        db, repos = self._db()
        try:
            rec = repos.mcp_servers.get(server_id)
            if not rec:
                raise ValueError("Server not found")
            # disconnect if connected before structural changes
            structural = any(k in updates for k in ("transport", "endpoint", "args", "env", "auth_config", "config"))
            if structural and server_id in self._servers:
                self.disconnect(server_id)
            rec = repos.mcp_servers.update(server_id, updates)
            db.commit()
            return self.get_server(server_id) or {}
        finally:
            db.close()

    def delete_server(self, server_id: str) -> Dict[str, Any]:
        db, repos = self._db()
        try:
            rec = repos.mcp_servers.get(server_id)
            if not rec:
                raise ValueError("Server not found")
            try:
                self.disconnect(server_id)
            except Exception:
                pass
            # prevent deleting built-in internal defaults? allow delete but they may be re-seeded on next ensure_defaults
            repos.mcp_servers.delete(server_id)
            db.commit()
            return {"deleted": True, "id": server_id}
        finally:
            db.close()

    def list_servers(self) -> List[Dict[str, Any]]:
        db, repos = self._db()
        try:
            rows = repos.mcp_servers.list_all()
            out = []
            for r in rows:
                inst = self._servers.get(r.id)
                out.append(self._to_public_server(r, inst))
            return out
        finally:
            db.close()

    def get_server(self, server_id: str) -> Optional[Dict[str, Any]]:
        db, repos = self._db()
        try:
            r = repos.mcp_servers.get(server_id)
            if not r:
                return None
            inst = self._servers.get(r.id)
            return self._to_public_server(r, inst)
        finally:
            db.close()

    def get_server_record(self, server_id: str):
        db, repos = self._db()
        try:
            return repos.mcp_servers.get(server_id)
        finally:
            db.close()

    # ---- build/connect ----
    def _server_type_for(self, record) -> str:
        cfg = record.config or {}
        return (cfg.get("server_type") or record.endpoint or record.name or "").lower()

    def _build_instance(self, record) -> Optional[BaseMcpServer]:
        transport = (record.transport or "internal").lower()
        cfg = McpServerConfig(
            id=record.id,
            name=record.name,
            description=record.description or "",
            transport=transport,
            endpoint=record.endpoint or "",
            args=record.args or [],
            env=record.env or {},
            auth_config=record.auth_config or {},
            permissions=record.permissions or {},
            timeout_ms=int((record.config or {}).get("timeout_ms") or 30000),
            config=record.config or {},
        )
        if transport == "internal":
            stype = self._server_type_for(record)
            cls = SERVER_CLASSES.get(stype)
            if not cls:
                return None
            return cls(cfg)
        if transport in ("stdio", "streamable_http", "http"):
            return ExternalMcpServer(cfg)
        return None

    def _audit(self, **fields: Any) -> None:
        evt = {
            "server_id": fields.get("server_id"),
            "server_name": fields.get("server_name"),
            "tool_name": fields.get("tool_name"),
            "action": fields.get("action", "tool_call"),
            "success": bool(fields.get("success", False)),
            "arguments": _redact(fields.get("arguments")),
            "result": _redact(fields.get("result")),
            "error": fields.get("error"),
            "duration_ms": fields.get("duration_ms"),
            "created_at": datetime.utcnow().isoformat(),
        }
        self._audit_cache.append(evt)
        if len(self._audit_cache) > 500:
            self._audit_cache = self._audit_cache[-500:]
        try:
            db, repos = self._db()
            try:
                repos.mcp_audit.log(
                    server_id=evt["server_id"], server_name=evt["server_name"], tool_name=evt["tool_name"],
                    action=evt["action"], success=evt["success"], arguments=evt["arguments"], result=evt["result"],
                    error=evt["error"], duration_ms=evt["duration_ms"],
                )
                db.commit()
            finally:
                db.close()
        except Exception:
            pass

    def connect(self, server_id: str) -> Dict[str, Any]:
        db, repos = self._db()
        try:
            record = repos.mcp_servers.get(server_id)
            if not record:
                raise ValueError("Server not found")
            if record.enabled is False:
                raise ValueError("Server is disabled")
            # rebuild instance on connect to pick up config changes
            inst = self._servers.get(server_id)
            if inst and getattr(inst, "connected", False):
                # refresh discovery info
                tools = inst.list_tools()
                resources = inst.list_resources() if hasattr(inst, "list_resources") else []
                prompts = inst.list_prompts() if hasattr(inst, "list_prompts") else []
                caps = {"resources_list": resources, "prompts_list": prompts}
                repos.mcp_servers.update(server_id, {"connection_state": "connected", "discovered_tools": tools, "capabilities": {**(record.capabilities or {}), **caps}, "last_error": None})
                db.commit()
                return {"server_id": server_id, "status": "connected", "tools": tools, "resources": resources, "prompts": prompts}
            # close old if any
            if inst:
                try: inst.close()
                except Exception: pass
            inst = self._build_instance(record)
            if not inst:
                repos.mcp_servers.update(server_id, {"connection_state": "error", "last_error": "Unsupported server type/transport"})
                db.commit()
                raise ValueError(f"Unsupported MCP server type/transport: {record.endpoint}/{record.transport}")
            self._servers[server_id] = inst
            init_info = inst.initialize()
            tools = inst.list_tools()
            resources = inst.list_resources() if hasattr(inst, "list_resources") else []
            prompts = inst.list_prompts() if hasattr(inst, "list_prompts") else []
            capabilities = (init_info or {}).get("capabilities") or {}
            capabilities = {**capabilities, "resources_list": resources, "prompts_list": prompts}
            repos.mcp_servers.update(server_id, {
                "connection_state": "connected",
                "discovered_tools": tools,
                "server_info": (init_info or {}).get("server") or {},
                "capabilities": capabilities,
                "last_error": None,
                "last_connected_at": datetime.utcnow(),
            })
            db.commit()
            self._audit(server_id=server_id, server_name=record.name, action="connect", success=True, result={"tools": len(tools), "resources": len(resources), "prompts": len(prompts)})
            return {"server_id": server_id, "status": "connected", "initialize": _redact(init_info), "tools": tools, "resources": resources, "prompts": prompts}
        except Exception as e:
            try:
                repos.mcp_servers.update(server_id, {"connection_state": "error", "last_error": str(e)})
                db.commit()
            except Exception:
                pass
            try:
                self._audit(server_id=server_id, action="connect", success=False, error=str(e))
            except Exception:
                pass
            raise
        finally:
            db.close()

    def disconnect(self, server_id: str) -> Dict[str, Any]:
        inst = self._servers.pop(server_id, None)
        name = None
        if inst:
            name = getattr(getattr(inst, "config", None), "name", None)
            try:
                inst.disconnect() if hasattr(inst, "disconnect") else inst.close()
            except Exception:
                pass
        db, repos = self._db()
        try:
            rec = repos.mcp_servers.get(server_id)
            if rec:
                name = name or rec.name
                repos.mcp_servers.update(server_id, {"connection_state": "disconnected"})
                db.commit()
        finally:
            db.close()
        self._audit(server_id=server_id, server_name=name, action="disconnect", success=True)
        return {"server_id": server_id, "status": "disconnected"}

    def restart(self, server_id: str) -> Dict[str, Any]:
        self.disconnect(server_id)
        return self.connect(server_id)

    def health(self, server_id: str) -> Dict[str, Any]:
        inst = self._servers.get(server_id)
        rec = self.get_server(server_id)
        h = {"server_id": server_id, "connected": bool(inst and getattr(inst, "connected", False)), "status": (rec or {}).get("status")}
        if inst and hasattr(inst, "health"):
            try:
                h.update(inst.health() or {})
            except Exception:
                pass
        return h

    # ---- permissions / validation ----
    def _tool_permission(self, inst: BaseMcpServer, tool_name: str) -> str:
        tool = getattr(inst, "_tools", {}).get(tool_name)
        if tool and getattr(tool, "permission", None):
            return tool.permission
        return "read"

    def _check_permissions(self, record, inst: BaseMcpServer, tool_name: str, arguments: Dict[str, Any]) -> Optional[str]:
        perms = record.permissions or {}
        allowed_tools = perms.get("allowed_tools")
        denied_tools = perms.get("denied_tools") or []
        if tool_name in denied_tools:
            return f"Tool '{tool_name}' is denied by server policy"
        if isinstance(allowed_tools, list) and allowed_tools:
            if tool_name not in allowed_tools:
                return f"Tool '{tool_name}' is not in server allowlist"
        # tool-level permission class
        required = self._tool_permission(inst, tool_name)
        allow_classes = perms.get("allow") or ["read", "write", "execute", "destructive"]
        # normalize
        if isinstance(allow_classes, str):
            allow_classes = [allow_classes]
        if required not in allow_classes:
            return f"Tool '{tool_name}' requires '{required}' permission which is not allowed"
        # destructive/execute approval hint via config
        require_approval = (record.config or {}).get("require_approval_for") or []
        if required in require_approval or tool_name in ((record.config or {}).get("require_approval_tools") or []):
            # no interactive approval system wired here; enforce explicit opt-in flag
            approved = arguments.get("_approved")
            if approved is None:
                approved = arguments.get("approved")
            if not approved:
                return f"Tool '{tool_name}' requires explicit approval (approved=true)"
            # normalize so downstream tools can also check
            arguments["_approved"] = True
        return None

    def _validate_arguments(self, inst: BaseMcpServer, tool_name: str, arguments: Dict[str, Any]) -> Optional[str]:
        tool = getattr(inst, "_tools", {}).get(tool_name)
        schema = getattr(tool, "input_schema", None) if tool else None
        if not isinstance(schema, dict):
            return None
        # minimal validation: required fields and basic types
        req = schema.get("required") or []
        for r in req:
            if r not in arguments:
                return f"Missing required argument: {r}"
        props = schema.get("properties") or {}
        tmap = {"string": str, "integer": int, "number": (int, float), "boolean": bool, "object": dict, "array": list}
        for k, v in arguments.items():
            if k not in props or not isinstance(props[k], dict):
                continue
            ptype = props[k].get("type")
            if isinstance(ptype, str) and ptype in tmap:
                expected = tmap[ptype]
                # allow ints for numbers
                if ptype == "integer" and isinstance(v, bool):
                    return f"Argument '{k}' must be integer"
                if not isinstance(v, expected):
                    # be lenient: accept numeric strings not required; but fail clear mismatches
                    if ptype in ("string", "object", "array", "boolean") or (ptype == "integer" and not isinstance(v, int)) or (ptype == "number" and not isinstance(v, (int, float))):
                        if ptype == "integer" and isinstance(v, float) and v.is_integer():
                            continue
                        return f"Argument '{k}' must be of type {ptype}"
        return None

    # ---- invocation/discovery ----
    def call_tool(self, server_id: str, tool_name: str, arguments: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        args = copy.deepcopy(arguments or {})
        start = time.time()
        db, repos = self._db()
        record = None
        try:
            record = repos.mcp_servers.get(server_id)
            if not record:
                raise ValueError("Server not found")
            if record.enabled is False:
                raise ValueError("Server is disabled")
            inst = self._servers.get(server_id)
            if not inst or not getattr(inst, "connected", False):
                # release db before connect (connect manages its own db)
                db.close(); db = None
                self.connect(server_id)
                db, repos = self._db()
                record = repos.mcp_servers.get(server_id)
                inst = self._servers.get(server_id)
            if not inst or not getattr(inst, "connected", False):
                raise ValueError("Server not connected")

            # permission & validation
            perm_err = self._check_permissions(record, inst, tool_name, args)
            if perm_err:
                raise ValueError(perm_err)
            val_err = self._validate_arguments(inst, tool_name, args)
            if val_err:
                raise ValueError(val_err)

            result: ToolResult = inst.call_tool(tool_name, args)
            payload = {
                "server_id": server_id,
                "server_name": record.name if record else getattr(getattr(inst, "config", None), "name", None),
                "tool": tool_name,
                "arguments": _redact(args),
                "success": bool(result.success),
                "content": result.content,
                "error": result.error,
                "metadata": result.metadata or {},
                "duration_ms": int((time.time() - start) * 1000),
            }
            self._audit(server_id=server_id, server_name=payload["server_name"], tool_name=tool_name, action="tool_call", success=payload["success"], arguments=args, result={"content": result.content, "error": result.error}, error=result.error, duration_ms=payload["duration_ms"])
            return payload
        except Exception as e:
            err_payload = {
                "server_id": server_id,
                "server_name": record.name if record else None,
                "tool": tool_name,
                "arguments": _redact(args),
                "success": False,
                "content": None,
                "error": str(e),
                "metadata": {},
                "duration_ms": int((time.time() - start) * 1000),
            }
            self._audit(server_id=server_id, server_name=err_payload.get("server_name"), tool_name=tool_name, action="tool_call", success=False, arguments=args, result=None, error=str(e), duration_ms=err_payload["duration_ms"])
            raise
        finally:
            try:
                if db:
                    db.close()
            except Exception:
                pass

    def list_tools(self, server_id: Optional[str] = None) -> List[Dict[str, Any]]:
        if server_id:
            s = self.get_server(server_id)
            return s.get("discovered_tools", []) if s else []
        tools = []
        for s in self.list_servers():
            for t in s.get("discovered_tools", []):
                tools.append({"server_id": s["id"], "server_name": s["name"], **t})
        return tools

    def list_resources(self, server_id: Optional[str] = None) -> List[Dict[str, Any]]:
        if server_id:
            s = self.get_server(server_id)
            if not s:
                return []
            return s.get("resources") or []
        out = []
        for s in self.list_servers():
            for r in (s.get("resources") or []):
                out.append({"server_id": s["id"], "server_name": s["name"], **(r if isinstance(r, dict) else {"value": r})})
        return out

    def list_prompts(self, server_id: Optional[str] = None) -> List[Dict[str, Any]]:
        if server_id:
            s = self.get_server(server_id)
            if not s:
                return []
            return s.get("prompts") or []
        out = []
        for s in self.list_servers():
            for p in (s.get("prompts") or []):
                out.append({"server_id": s["id"], "server_name": s["name"], **(p if isinstance(p, dict) else {"value": p})})
        return out

    def audit_log(self, limit: int = 100, server_id: Optional[str] = None) -> List[Dict[str, Any]]:
        db, repos = self._db()
        try:
            events = repos.mcp_audit.recent(limit=limit, server_id=server_id)
            return [
                {
                    "id": e.id, "server_id": e.server_id, "server_name": e.server_name,
                    "tool_name": e.tool_name, "action": e.action, "success": e.success,
                    "arguments": _redact(e.arguments), "result": _redact(e.result),
                    "error": e.error, "duration_ms": e.duration_ms,
                    "created_at": e.created_at.isoformat() if e.created_at else None,
                }
                for e in events
            ]
        except Exception:
            # fallback to cache
            items = list(self._audit_cache)
            if server_id:
                items = [i for i in items if i.get("server_id") == server_id]
            return list(reversed(items[-limit:]))
        finally:
            db.close()


mcp_manager = McpManager()
