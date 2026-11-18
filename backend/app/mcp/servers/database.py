"""Database MCP server: schema inspection and permitted queries (SQLite-focused)."""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.mcp.base import BaseMcpServer, McpServerConfig, ToolDefinition, ToolResult


class DatabaseMcpServer(BaseMcpServer):
    server_type = "database"

    def __init__(self, config: McpServerConfig):
        super().__init__(config)
        cfg = config.config or {}
        root = (config.args[0] if config.args else None) or cfg.get("root") or config.env.get("ROOT") or os.getcwd()
        self.root = Path(root).resolve()
        self.read_only = bool(cfg.get("read_only", True))
        self.max_rows = int(cfg.get("max_rows") or 200)
        self._register_tools()

    def _resolve_db(self, args: Dict[str, Any]) -> Path:
        db = args.get("database") or args.get("path") or "nexus_ai.db"
        p = (self.root / db).resolve() if not os.path.isabs(str(db)) else Path(str(db)).resolve()
        try:
            p.relative_to(self.root)
        except Exception:
            if p != self.root and self.root not in p.parents:
                raise ValueError("Database path escapes allowed root")
        return p

    def _register_tools(self) -> None:
        t = self.register_tool
        t(ToolDefinition("db.list_connections", "List allowed database connections", {"type":"object","properties":{}}, "read"), self.list_connections)
        t(ToolDefinition("db.inspect_schema", "Inspect database schema", {"type":"object","properties":{"database":{"type":"string"}},"required":[]}, "read"), self.inspect_schema)
        t(ToolDefinition("db.list_tables", "List tables/views", {"type":"object","properties":{"database":{"type":"string"}}}, "read"), self.list_tables)
        t(ToolDefinition("db.execute_query", "Execute a permitted SQL query", {"type":"object","properties":{"database":{"type":"string"},"query":{"type":"string"},"params":{"type":"array"},"limit":{"type":"integer"},"allow_write":{"type":"boolean"}},"required":["query"]}, "read"), self.execute_query)

    def list_connections(self, args: Dict[str, Any]) -> ToolResult:
        dbs = []
        seen = set()
        for name in ["nexus_ai.db", "backend/nexus_ai.db"]:
            p = (self.root / name).resolve()
            if p.exists():
                key = str(p)
                if key not in seen:
                    seen.add(key)
                    dbs.append({"name": name, "path": str(p)})
        for p in self.root.glob("*.db"):
            key = str(p.resolve())
            if key not in seen:
                seen.add(key)
                dbs.append({"name": p.name, "path": str(p.resolve())})
        return ToolResult(success=True, content={"connections": dbs})

    def _connect(self, path: Path):
        if not path.exists():
            raise FileNotFoundError(f"Database not found: {path}")
        conn = sqlite3.connect(str(path), timeout=10)
        conn.row_factory = sqlite3.Row
        return conn

    def list_tables(self, args: Dict[str, Any]) -> ToolResult:
        try:
            path = self._resolve_db(args)
            conn = self._connect(path)
            try:
                cur = conn.cursor()
                cur.execute("SELECT name, type FROM sqlite_master WHERE type IN ('table','view') ORDER BY name")
                rows = [dict(r) for r in cur.fetchall()]
                return ToolResult(success=True, content={"database": str(path), "tables": rows, "count": len(rows)})
            finally:
                conn.close()
        except Exception as e:
            return ToolResult(success=False, error=str(e))

    def inspect_schema(self, args: Dict[str, Any]) -> ToolResult:
        try:
            path = self._resolve_db(args)
            conn = self._connect(path)
            try:
                cur = conn.cursor()
                cur.execute("SELECT name, type, sql FROM sqlite_master WHERE type IN ('table','view') ORDER BY name")
                objects = [dict(r) for r in cur.fetchall()]
                schema = []
                for obj in objects:
                    if obj.get("type") == "table":
                        cur.execute(f"PRAGMA table_info('{obj['name']}')")
                        cols = [dict(r) for r in cur.fetchall()]
                        schema.append({"name": obj["name"], "type": obj["type"], "sql": obj.get("sql"), "columns": cols})
                    else:
                        schema.append(obj)
                return ToolResult(success=True, content={"database": str(path), "schema": schema})
            finally:
                conn.close()
        except Exception as e:
            return ToolResult(success=False, error=str(e))

    def execute_query(self, args: Dict[str, Any]) -> ToolResult:
        try:
            path = self._resolve_db(args)
            query = str(args.get("query", "")).strip()
            if not query:
                return ToolResult(success=False, error="query is required")
            ql = query.lstrip().lower()
            read_only_prefixes = ("select", "with", "pragma", "explain")
            is_read = ql.startswith(read_only_prefixes)
            allow_write = bool(args.get("allow_write", False))
            if self.read_only and not is_read:
                return ToolResult(success=False, error="Write/destructive queries are disabled (read-only mode)")
            if not self.read_only and not is_read and not allow_write:
                return ToolResult(success=False, error="Non-read query requires allow_write=true")
            # even in non-read-only, block obviously dangerous multi-statement patterns crudely
            if ";" in query.strip().rstrip(";"):
                # allow simple trailing semicolon only
                if query.strip().count(";") > 1:
                    return ToolResult(success=False, error="Multiple SQL statements are not permitted")
            limit = min(int(args.get("limit", self.max_rows)), 1000)
            params = args.get("params") or []
            if not isinstance(params, list):
                return ToolResult(success=False, error="params must be an array")
            conn = self._connect(path)
            try:
                cur = conn.cursor()
                cur.execute(query, params)
                if cur.description:
                    cols = [d[0] for d in cur.description]
                    rows = [dict(zip(cols, r)) for r in cur.fetchmany(limit)]
                    return ToolResult(success=True, content={"database": str(path), "columns": cols, "rows": rows, "row_count": len(rows), "truncated": len(rows) >= limit})
                if not is_read:
                    conn.commit()
                return ToolResult(success=True, content={"database": str(path), "rowcount": cur.rowcount, "lastrowid": cur.lastrowid})
            finally:
                conn.close()
        except Exception as e:
            return ToolResult(success=False, error=str(e))
