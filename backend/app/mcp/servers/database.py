"""Database MCP server: schema inspection and permitted queries (SQLite-focused)."""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Any, Dict, List

from app.mcp.base import BaseMcpServer, McpServerConfig, ToolDefinition, ToolResult


class DatabaseMcpServer(BaseMcpServer):
    server_type = "database"

    def __init__(self, config: McpServerConfig):
        super().__init__(config)
        root = (config.args[0] if config.args else None) or config.env.get("ROOT") or os.getcwd()
        self.root = Path(root).resolve()
        self._register_tools()

    def _resolve_db(self, args: Dict[str, Any]) -> Path:
        db = args.get("database") or args.get("path") or "nexus_ai.db"
        p = (self.root / db).resolve() if not os.path.isabs(str(db)) else Path(str(db)).resolve()
        try:
            p.relative_to(self.root)
        except Exception:
            # allow explicit absolute inside root only
            if p != self.root and self.root not in p.parents:
                raise ValueError("Database path escapes allowed root")
        return p

    def _register_tools(self) -> None:
        t = self.register_tool
        t(ToolDefinition("db.list_connections", "List allowed database connections", {"type":"object","properties":{}}, "read"), self.list_connections)
        t(ToolDefinition("db.inspect_schema", "Inspect database schema", {"type":"object","properties":{"database":{"type":"string"}},"required":[]}, "read"), self.inspect_schema)
        t(ToolDefinition("db.execute_query", "Execute a permitted SQL query", {"type":"object","properties":{"database":{"type":"string"},"query":{"type":"string"},"params":{"type":"array"},"limit":{"type":"integer"}},"required":["query"]}, "read"), self.execute_query)

    def list_connections(self, args: Dict[str, Any]) -> ToolResult:
        dbs = []
        for name in ["nexus_ai.db", "backend/nexus_ai.db"]:
            p = (self.root / name).resolve()
            if p.exists():
                dbs.append({"name": name, "path": str(p)})
        # also scan for *.db in root (shallow)
        for p in self.root.glob("*.db"):
            item = {"name": p.name, "path": str(p)}
            if item not in dbs:
                dbs.append(item)
        return ToolResult(success=True, content={"connections": dbs})

    def _connect(self, path: Path):
        if not path.exists():
            raise FileNotFoundError(f"Database not found: {path}")
        conn = sqlite3.connect(str(path))
        conn.row_factory = sqlite3.Row
        return conn

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
                    if obj["type"] == "table":
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
            # safety: allow read-only statements by default
            allowed = ("select", "with", "pragma", "explain")
            if not ql.startswith(allowed):
                return ToolResult(success=False, error="Only read-only queries are permitted (SELECT/WITH/PRAGMA/EXPLAIN)")
            limit = int(args.get("limit", 200))
            params = args.get("params") or []
            conn = self._connect(path)
            try:
                cur = conn.cursor()
                cur.execute(query, params)
                if cur.description:
                    cols = [d[0] for d in cur.description]
                    rows = [dict(zip(cols, r)) for r in cur.fetchmany(limit)]
                    return ToolResult(success=True, content={"database": str(path), "columns": cols, "rows": rows, "row_count": len(rows)})
                conn.commit()
                return ToolResult(success=True, content={"database": str(path), "rowcount": cur.rowcount})
            finally:
                conn.close()
        except Exception as e:
            return ToolResult(success=False, error=str(e))
