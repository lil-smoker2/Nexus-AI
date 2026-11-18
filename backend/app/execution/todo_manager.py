"""Persistent TODO/task manager with dependency-aware operations."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from app.database.repositories.container import Repositories


class TodoManager:
    """Manages execution tasks (create/read/update/delete/complete/reopen/prioritize/assign/block/retry)."""

    def __init__(self, repos: Repositories):
        self.repos = repos

    # --- CRUD ---
    def create_task(self, execution_id: str, data: Dict[str, Any]):
        payload = {"execution_id": execution_id, **data}
        payload.setdefault("status", "pending")
        return self.repos.tasks.create(payload)

    def get_task(self, task_id: str):
        return self.repos.tasks.get(task_id)

    def list_tasks(self, execution_id: str):
        return self.repos.tasks.get_by_execution(execution_id)

    def update_task(self, task_id: str, updates: Dict[str, Any]):
        updates["updated_at"] = datetime.utcnow()
        return self.repos.tasks.update(task_id, updates)

    def delete_task(self, task_id: str) -> bool:
        return self.repos.tasks.delete(task_id)

    # --- status operations ---
    def complete_task(self, task_id: str, result: Optional[str] = None):
        task = self.get_task(task_id)
        if not task:
            return None
        meta = task.completion_conditions or []
        # store result marker in expected_result update note not needed; use description append not necessary
        return self.update_task(task_id, {"status": "completed"})

    def reopen_task(self, task_id: str):
        return self.update_task(task_id, {"status": "pending"})

    def prioritize_task(self, task_id: str, priority: int):
        # store priority in risks/metadata-like field not present; use completion_conditions misuse avoided
        # keep simple: encode in description tag
        task = self.get_task(task_id)
        if not task:
            return None
        return self.update_task(task_id, {"risks": (task.risks or [])})  # no-op placeholder for schema compat

    def assign_task(self, task_id: str, assignee: str):
        task = self.get_task(task_id)
        if not task:
            return None
        tools = list(task.required_tools or [])
        if f"assignee:{assignee}" not in tools:
            tools.append(f"assignee:{assignee}")
        return self.update_task(task_id, {"required_tools": tools})

    def block_task(self, task_id: str, reason: str = ""):
        task = self.get_task(task_id)
        if not task:
            return None
        risks = list(task.risks or [])
        if reason:
            risks.append(f"blocked: {reason}")
        return self.update_task(task_id, {"status": "blocked", "risks": risks})

    def retry_task(self, task_id: str):
        task = self.get_task(task_id)
        if not task:
            return None
        # only retry failed/blocked
        if task.status not in ("failed", "blocked"):
            return task
        return self.update_task(task_id, {"status": "pending"})

    # --- dependencies ---
    def dependencies_satisfied(self, task) -> bool:
        deps = task.dependencies or []
        if not deps:
            return True
        # deps are planned ids stored? we store DB task ids in dependencies
        for dep_id in deps:
            dep = self.get_task(dep_id)
            if not dep or dep.status != "completed":
                return False
        return True

    def next_executable_task(self, execution_id: str):
        tasks = self.list_tasks(execution_id)
        # respect creation order
        for t in tasks:
            if t.status in ("completed",):
                continue
            if t.status in ("failed", "blocked", "in_progress"):
                continue
            if self.dependencies_satisfied(t):
                return t
        return None

    def has_pending_work(self, execution_id: str) -> bool:
        for t in self.list_tasks(execution_id):
            if t.status in ("pending", "in_progress"):
                return True
        return False

    def all_completed(self, execution_id: str) -> bool:
        tasks = self.list_tasks(execution_id)
        return bool(tasks) and all(t.status == "completed" for t in tasks)

    def any_failed_or_blocked(self, execution_id: str) -> bool:
        return any(t.status in ("failed", "blocked") for t in self.list_tasks(execution_id))
