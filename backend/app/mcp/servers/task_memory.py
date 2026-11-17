"""Task and Memory MCP server backed by NEXUS database repositories."""

from __future__ import annotations

from typing import Any, Dict, Optional

from app.mcp.base import BaseMcpServer, McpServerConfig, ToolDefinition, ToolResult
from app.database.session import SessionLocal
from app.database.repositories.container import Repositories


class TaskMemoryMcpServer(BaseMcpServer):
    server_type = "task_memory"

    def __init__(self, config: McpServerConfig):
        super().__init__(config)
        self._register_tools()

    def _repos(self) -> Repositories:
        db = SessionLocal()
        return Repositories(db)

    def _default_user_id(self, repos: Repositories) -> str:
        user = repos.users.get_by_username("default")
        if not user:
            user = repos.users.create_user("default")
        return user.id

    def _register_tools(self) -> None:
        t = self.register_tool
        # Tasks
        t(ToolDefinition("task.create", "Create a task", {"type":"object","properties":{"title":{"type":"string"},"description":{"type":"string"},"status":{"type":"string"},"execution_id":{"type":"string"}},"required":["title"]}, "write"), self.task_create)
        t(ToolDefinition("task.list", "List tasks", {"type":"object","properties":{"status":{"type":"string"},"limit":{"type":"integer"}}}, "read"), self.task_list)
        t(ToolDefinition("task.get", "Get a task", {"type":"object","properties":{"id":{"type":"string"}},"required":["id"]}, "read"), self.task_get)
        t(ToolDefinition("task.update", "Update a task", {"type":"object","properties":{"id":{"type":"string"},"status":{"type":"string"},"title":{"type":"string"},"description":{"type":"string"}},"required":["id"]}, "write"), self.task_update)
        # Memory
        t(ToolDefinition("memory.store", "Store a memory", {"type":"object","properties":{"category":{"type":"string"},"content":{"type":"string"},"source":{"type":"string"},"importance":{"type":"integer"}},"required":["category","content"]}, "write"), self.memory_store)
        t(ToolDefinition("memory.search", "Search/retrieve memories", {"type":"object","properties":{"category":{"type":"string"},"query":{"type":"string"},"limit":{"type":"integer"}}}, "read"), self.memory_search)
        t(ToolDefinition("memory.delete", "Delete a memory", {"type":"object","properties":{"id":{"type":"string"}},"required":["id"]}, "destructive"), self.memory_delete)

    def _task_dict(self, task) -> Dict[str, Any]:
        return {"id": task.id, "title": task.title, "description": task.description, "status": task.status, "execution_id": task.execution_id, "created_at": str(task.created_at)}

    def _mem_dict(self, m) -> Dict[str, Any]:
        return {"id": m.id, "user_id": m.user_id, "category": m.category, "content": m.content, "source": m.source, "importance": m.importance, "created_at": str(m.created_at)}

    def task_create(self, args: Dict[str, Any]) -> ToolResult:
        repos = self._repos()
        try:
            obj = repos.tasks.create({
                "title": str(args.get("title", "")).strip() or "Untitled task",
                "description": args.get("description"),
                "status": args.get("status") or "pending",
                "execution_id": args.get("execution_id"),
            })
            return ToolResult(success=True, content=self._task_dict(obj))
        except Exception as e:
            return ToolResult(success=False, error=str(e))
        finally:
            repos.db.close()

    def task_list(self, args: Dict[str, Any]) -> ToolResult:
        repos = self._repos()
        try:
            status = args.get("status")
            limit = int(args.get("limit", 50))
            if status:
                tasks = repos.tasks.get_by_status(status, limit=limit)
            else:
                tasks = repos.tasks.get_multi(limit=limit)
            return ToolResult(success=True, content={"tasks": [self._task_dict(t) for t in tasks], "count": len(tasks)})
        except Exception as e:
            return ToolResult(success=False, error=str(e))
        finally:
            repos.db.close()

    def task_get(self, args: Dict[str, Any]) -> ToolResult:
        repos = self._repos()
        try:
            t = repos.tasks.get(str(args.get("id")))
            if not t:
                return ToolResult(success=False, error="Task not found")
            return ToolResult(success=True, content=self._task_dict(t))
        except Exception as e:
            return ToolResult(success=False, error=str(e))
        finally:
            repos.db.close()

    def task_update(self, args: Dict[str, Any]) -> ToolResult:
        repos = self._repos()
        try:
            tid = str(args.get("id"))
            updates = {k: v for k, v in {"status": args.get("status"), "title": args.get("title"), "description": args.get("description")}.items() if v is not None}
            t = repos.tasks.update(tid, updates)
            if not t:
                return ToolResult(success=False, error="Task not found")
            return ToolResult(success=True, content=self._task_dict(t))
        except Exception as e:
            return ToolResult(success=False, error=str(e))
        finally:
            repos.db.close()

    def memory_store(self, args: Dict[str, Any]) -> ToolResult:
        repos = self._repos()
        try:
            user_id = self._default_user_id(repos)
            m = repos.memories.create({
                "user_id": user_id,
                "category": str(args.get("category", "general")),
                "content": str(args.get("content", "")),
                "source": args.get("source"),
                "importance": int(args.get("importance", 5)),
            })
            return ToolResult(success=True, content=self._mem_dict(m))
        except Exception as e:
            return ToolResult(success=False, error=str(e))
        finally:
            repos.db.close()

    def memory_search(self, args: Dict[str, Any]) -> ToolResult:
        repos = self._repos()
        try:
            user_id = self._default_user_id(repos)
            category = args.get("category")
            query = (args.get("query") or "").lower()
            limit = int(args.get("limit", 50))
            mems = repos.memories.get_by_user(user_id, category=category, limit=limit)
            if query:
                mems = [m for m in mems if query in (m.content or "").lower()]
            return ToolResult(success=True, content={"memories": [self._mem_dict(m) for m in mems], "count": len(mems)})
        except Exception as e:
            return ToolResult(success=False, error=str(e))
        finally:
            repos.db.close()

    def memory_delete(self, args: Dict[str, Any]) -> ToolResult:
        repos = self._repos()
        try:
            ok = repos.memories.delete(str(args.get("id")))
            if not ok:
                return ToolResult(success=False, error="Memory not found")
            return ToolResult(success=True, content={"id": args.get("id"), "deleted": True})
        except Exception as e:
            return ToolResult(success=False, error=str(e))
        finally:
            repos.db.close()
