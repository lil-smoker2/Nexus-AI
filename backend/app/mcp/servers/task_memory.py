"""Task and Memory MCP server backed by NEXUS database repositories."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

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
        t(ToolDefinition("task.create", "Create a task/TODO", {"type":"object","properties":{"title":{"type":"string"},"description":{"type":"string"},"expected_result":{"type":"string"},"status":{"type":"string"},"execution_id":{"type":"string"},"parent_task_id":{"type":"string"},"dependencies":{"type":"array"}},"required":["title"]}, "write"), self.task_create)
        t(ToolDefinition("task.list", "List tasks", {"type":"object","properties":{"status":{"type":"string"},"execution_id":{"type":"string"},"limit":{"type":"integer"}}}, "read"), self.task_list)
        t(ToolDefinition("task.get", "Get a task", {"type":"object","properties":{"id":{"type":"string"}},"required":["id"]}, "read"), self.task_get)
        t(ToolDefinition("task.update", "Update a task", {"type":"object","properties":{"id":{"type":"string"},"status":{"type":"string"},"title":{"type":"string"},"description":{"type":"string"},"expected_result":{"type":"string"},"dependencies":{"type":"array"}},"required":["id"]}, "write"), self.task_update)
        t(ToolDefinition("task.set_status", "Set task status", {"type":"object","properties":{"id":{"type":"string"},"status":{"type":"string"}},"required":["id","status"]}, "write"), self.task_set_status)
        t(ToolDefinition("task.delete", "Delete a task", {"type":"object","properties":{"id":{"type":"string"}},"required":["id"]}, "destructive"), self.task_delete)
        # Memory
        t(ToolDefinition("memory.store", "Store a memory", {"type":"object","properties":{"category":{"type":"string"},"content":{"type":"string"},"source":{"type":"string"},"importance":{"type":"integer"},"user_id":{"type":"string"}},"required":["category","content"]}, "write"), self.memory_store)
        t(ToolDefinition("memory.search", "Search/retrieve memories", {"type":"object","properties":{"category":{"type":"string"},"query":{"type":"string"},"limit":{"type":"integer"},"user_id":{"type":"string"}}}, "read"), self.memory_search)
        t(ToolDefinition("memory.get", "Get a memory by id", {"type":"object","properties":{"id":{"type":"string"}},"required":["id"]}, "read"), self.memory_get)
        t(ToolDefinition("memory.delete", "Delete a memory", {"type":"object","properties":{"id":{"type":"string"}},"required":["id"]}, "destructive"), self.memory_delete)
        t(ToolDefinition("conversation.unresolved_topics", "Retrieve unresolved conversation topics (placeholder/summary)", {"type":"object","properties":{"conversation_id":{"type":"string"},"limit":{"type":"integer"}}}, "read"), self.unresolved_topics)

    def _task_dict(self, task) -> Dict[str, Any]:
        return {
            "id": task.id, "title": task.title, "description": task.description, "expected_result": getattr(task, "expected_result", None),
            "status": task.status, "execution_id": task.execution_id, "parent_task_id": getattr(task, "parent_task_id", None),
            "dependencies": task.dependencies or [], "created_at": str(task.created_at), "updated_at": str(getattr(task, "updated_at", None)),
        }

    def _mem_dict(self, m) -> Dict[str, Any]:
        return {"id": m.id, "user_id": m.user_id, "category": m.category, "content": m.content, "source": m.source, "importance": m.importance, "created_at": str(m.created_at)}

    def task_create(self, args: Dict[str, Any]) -> ToolResult:
        repos = self._repos()
        try:
            obj = repos.tasks.create({
                "title": str(args.get("title", "")).strip() or "Untitled task",
                "description": args.get("description"),
                "expected_result": args.get("expected_result"),
                "status": args.get("status") or "pending",
                "execution_id": args.get("execution_id"),
                "parent_task_id": args.get("parent_task_id"),
                "dependencies": args.get("dependencies") or [],
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
            execution_id = args.get("execution_id")
            limit = int(args.get("limit", 50))
            if execution_id:
                tasks = repos.tasks.get_by_execution(str(execution_id))
            elif status:
                tasks = repos.tasks.get_by_status(str(status), limit=limit)
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
            allowed = ["status", "title", "description", "expected_result", "dependencies", "parent_task_id"]
            updates = {k: args.get(k) for k in allowed if k in args and args.get(k) is not None}
            t = repos.tasks.update(tid, updates)
            if not t:
                return ToolResult(success=False, error="Task not found")
            return ToolResult(success=True, content=self._task_dict(t))
        except Exception as e:
            return ToolResult(success=False, error=str(e))
        finally:
            repos.db.close()

    def task_set_status(self, args: Dict[str, Any]) -> ToolResult:
        repos = self._repos()
        try:
            tid = str(args.get("id"))
            status = str(args.get("status"))
            t = repos.tasks.update(tid, {"status": status})
            if not t:
                return ToolResult(success=False, error="Task not found")
            return ToolResult(success=True, content=self._task_dict(t))
        except Exception as e:
            return ToolResult(success=False, error=str(e))
        finally:
            repos.db.close()

    def task_delete(self, args: Dict[str, Any]) -> ToolResult:
        repos = self._repos()
        try:
            ok = repos.tasks.delete(str(args.get("id")))
            if not ok:
                return ToolResult(success=False, error="Task not found")
            return ToolResult(success=True, content={"id": args.get("id"), "deleted": True})
        except Exception as e:
            return ToolResult(success=False, error=str(e))
        finally:
            repos.db.close()

    def memory_store(self, args: Dict[str, Any]) -> ToolResult:
        repos = self._repos()
        try:
            user_id = str(args.get("user_id") or self._default_user_id(repos))
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
            user_id = str(args.get("user_id") or self._default_user_id(repos))
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

    def memory_get(self, args: Dict[str, Any]) -> ToolResult:
        repos = self._repos()
        try:
            m = repos.memories.get(str(args.get("id")))
            if not m:
                return ToolResult(success=False, error="Memory not found")
            return ToolResult(success=True, content=self._mem_dict(m))
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

    def unresolved_topics(self, args: Dict[str, Any]) -> ToolResult:
        # No dedicated unresolved-topic store yet; return empty structured result for MCP contract.
        return ToolResult(success=True, content={"conversation_id": args.get("conversation_id"), "topics": [], "count": 0, "note": "Unresolved topic tracking not yet persisted; no items found."})
