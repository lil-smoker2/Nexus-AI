"""Autonomous execution engine: plan, execute loop, checkpoints, recovery, history."""

from __future__ import annotations

import time
import uuid
from dataclasses import asdict
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.database.session import SessionLocal
from app.database.repositories.container import Repositories
from app.execution.planner import TaskPlanner, Plan, PlannedTask
from app.execution.todo_manager import TodoManager
from app.mcp.manager import mcp_manager


TERMINAL = {"completed", "failed", "stopped", "blocked"}


class ExecutionEngine:
    """Runs objectives through plan -> execute -> verify -> report cycle."""

    def __init__(self):
        self.planner = TaskPlanner()

    # --- helpers ---
    def _db(self):
        db = SessionLocal()
        return db, Repositories(db)

    def _append(self, items: Optional[List[Any]], item: Any) -> List[Any]:
        lst = list(items or [])
        lst.append(item)
        return lst

    def _snapshot(self, repos: Repositories, execution_id: str, label: str) -> Dict[str, Any]:
        tasks = repos.tasks.get_by_execution(execution_id)
        return {
            "id": str(uuid.uuid4())[:8],
            "label": label,
            "at": datetime.utcnow().isoformat(),
            "tasks": [{"id": t.id, "title": t.title, "status": t.status} for t in tasks],
        }

    def _persist_checkpoint(self, repos: Repositories, execution_id: str, label: str):
        ex = repos.executions.get(execution_id)
        if not ex:
            return None
        cps = self._append(ex.checkpoints, self._snapshot(repos, execution_id, label))
        return repos.executions.update(execution_id, {"checkpoints": cps})

    def _record_history(self, repos: Repositories, execution_id: str, **fields):
        ex = repos.executions.get(execution_id)
        if not ex:
            return None
        updates = {}
        for k, v in fields.items():
            if k in ("tool_calls", "tool_results", "errors", "verification_evidence", "approvals", "completed_tasks", "pending_tasks", "checkpoints"):
                updates[k] = self._append(getattr(ex, k), v) if not isinstance(v, list) or k.endswith("_set") else v
            else:
                updates[k] = v
        # handle list appends properly
        for k in ("tool_calls", "tool_results", "errors", "verification_evidence", "approvals"):
            if k in fields:
                updates[k] = self._append(getattr(ex, k), fields[k])
        repos.executions.update(execution_id, updates)
        return repos.executions.get(execution_id)

    # --- planning / task materialization ---
    def _materialize_plan(self, repos: Repositories, execution_id: str, plan: Plan) -> List[Any]:
        todo = TodoManager(repos)
        id_map: Dict[str, str] = {}
        created = []
        for pt in plan.tasks:
            # resolve dependencies from planned ids to DB ids
            dep_db_ids = [id_map[d] for d in (pt.dependencies or []) if d in id_map]
            t = todo.create_task(execution_id, {
                "title": pt.title,
                "description": pt.description,
                "expected_result": pt.expected_result,
                "status": "pending",
                "required_tools": pt.required_tools or [],
                "completion_conditions": pt.completion_conditions or [],
                "risks": pt.risks or [],
                "dependencies": dep_db_ids,
            })
            id_map[pt.id] = t.id
            # stash action on task via risks? no, not ideal. store in execution pending_tasks map by db id
            created.append((t, pt))
        return created

    def _store_plan_state(self, repos: Repositories, execution_id: str, plan: Plan, created_pairs):
        pending = []
        action_map = {}
        for t, pt in created_pairs:
            pending.append({"task_id": t.id, "title": t.title, "status": t.status})
            action_map[t.id] = pt.action or {}
        plan_payload = plan.to_dict()
        # embed actions for executor
        plan_payload["task_actions"] = action_map
        repos.executions.update(execution_id, {
            "status": "running",
            "plan_version": (repos.executions.get(execution_id).plan_version or 0) + 1,
            "pending_tasks": pending,
            "completed_tasks": [],
            "errors": [],
            "tool_calls": [],
            "tool_results": [],
            "verification_evidence": [],
            "checkpoints": self._append(repos.executions.get(execution_id).checkpoints, {
                "id": str(uuid.uuid4())[:8], "label": "plan_created", "at": datetime.utcnow().isoformat(), "plan": plan_payload,
            }),
            "final_report": None,
        })
        return plan_payload

    # --- tool/action execution ---
    def _resolve_server_id(self, server_name: str) -> Optional[str]:
        try:
            for s in mcp_manager.list_servers():
                if s.get("name") == server_name or s.get("endpoint") == server_name or s.get("id") == server_name:
                    return s["id"]
        except Exception:
            return None
        return None

    def _execute_action(self, action: Dict[str, Any]) -> Dict[str, Any]:
        atype = (action or {}).get("type", "analysis")
        if atype == "tool":
            server = action.get("server")
            tool = action.get("tool")
            args = action.get("arguments") or {}
            sid = self._resolve_server_id(server) if server else None
            if not sid:
                return {"ok": False, "error": f"MCP server not found: {server}", "action": action}
            try:
                res = mcp_manager.call_tool(sid, tool, args)
                return {"ok": bool(res.get("success")), "result": res, "action": action}
            except Exception as e:
                return {"ok": False, "error": str(e), "action": action}
        elif atype == "noop":
            return {"ok": True, "result": {"message": "noop"}, "action": action}
        else:
            note = action.get("note") or "analysis step"
            return {"ok": True, "result": {"message": f"Completed: {note}"}, "action": action}

    # --- main loop ---
    def create_and_run(self, objective: str, agent_id: str = "companion", conversation_id: Optional[str] = None, auto_run: bool = True) -> Dict[str, Any]:
        db, repos = self._db()
        try:
            ex = repos.executions.create_execution(agent_id=agent_id, user_objective=objective, conversation_id=conversation_id)
            execution_id = ex.id
            plan = self.planner.plan(objective)
            created_pairs = self._materialize_plan(repos, execution_id, plan)
            plan_payload = self._store_plan_state(repos, execution_id, plan, created_pairs)
            if not auto_run:
                repos.executions.update(execution_id, {"status": "pending"})
                return self.get_status(execution_id, repos=repos)
            return self._run_loop(repos, execution_id, plan_payload)
        finally:
            db.close()

    def _plan_actions(self, repos: Repositories, execution_id: str) -> Dict[str, Any]:
        ex = repos.executions.get(execution_id)
        if not ex:
            return {}
        for cp in reversed(ex.checkpoints or []):
            if isinstance(cp, dict) and "plan" in cp and isinstance(cp["plan"], dict):
                return cp["plan"].get("task_actions") or {}
        return {}

    def _run_loop(self, repos: Repositories, execution_id: str, plan_payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        todo = TodoManager(repos)
        actions = (plan_payload or {}).get("task_actions") or self._plan_actions(repos, execution_id)
        max_steps = 200
        steps = 0
        while steps < max_steps:
            steps += 1
            ex = repos.executions.get(execution_id)
            if not ex:
                break
            if ex.status in ("paused", "stopped"):
                break
            # pick next executable
            task = todo.next_executable_task(execution_id)
            if not task:
                tasks = todo.list_tasks(execution_id)
                if tasks and all(t.status == "completed" for t in tasks):
                    report = self._build_report(repos, execution_id, final_status="completed")
                    repos.executions.update(execution_id, {"status": "completed", "current_task": None, "final_report": report})
                    self._persist_checkpoint(repos, execution_id, "completed")
                    break
                if any(t.status in ("failed", "blocked") for t in tasks):
                    report = self._build_report(repos, execution_id, final_status="failed")
                    status = "blocked" if any(t.status == "blocked" for t in tasks) and not any(t.status == "failed" for t in tasks) else "failed"
                    repos.executions.update(execution_id, {"status": status, "current_task": None, "final_report": report})
                    self._persist_checkpoint(repos, execution_id, status)
                    break
                # no executable because deps unmet but pending exist -> blocked
                if any(t.status == "pending" for t in tasks):
                    report = self._build_report(repos, execution_id, final_status="blocked")
                    repos.executions.update(execution_id, {"status": "blocked", "current_task": None, "final_report": report, "errors": self._append(ex.errors, {"error": "No executable task; dependencies unmet or tasks blocked."})})
                    self._persist_checkpoint(repos, execution_id, "blocked")
                break

            # execute task
            repos.executions.update(execution_id, {"status": "running", "current_task": task.id})
            todo.update_task(task.id, {"status": "in_progress"})
            self._persist_checkpoint(repos, execution_id, f"start:{task.title}")

            action = actions.get(task.id) or {"type": "analysis", "note": task.title}
            call_record = {"task_id": task.id, "title": task.title, "action": action, "at": datetime.utcnow().isoformat()}
            outcome = self._execute_action(action)
            ok = bool(outcome.get("ok"))
            result_record = {"task_id": task.id, "title": task.title, "ok": ok, "outcome": outcome, "at": datetime.utcnow().isoformat()}

            ex = repos.executions.get(execution_id)
            tool_calls = self._append(ex.tool_calls, call_record)
            tool_results = self._append(ex.tool_results, result_record)
            verification = self._append(ex.verification_evidence, {"task_id": task.id, "verified": ok, "detail": outcome.get("error") or "ok"})

            if ok:
                todo.update_task(task.id, {"status": "completed"})
                completed = self._append(ex.completed_tasks, {"task_id": task.id, "title": task.title, "at": datetime.utcnow().isoformat()})
                pending = [p for p in (ex.pending_tasks or []) if p.get("task_id") != task.id]
                repos.executions.update(execution_id, {"tool_calls": tool_calls, "tool_results": tool_results, "verification_evidence": verification, "completed_tasks": completed, "pending_tasks": pending, "current_task": None})
            else:
                err = outcome.get("error") or "Task failed"
                todo.update_task(task.id, {"status": "failed", "risks": self._append(task.risks, f"error: {err}")})
                errors = self._append(ex.errors, {"task_id": task.id, "title": task.title, "error": err, "at": datetime.utcnow().isoformat()})
                pending = [p for p in (ex.pending_tasks or []) if p.get("task_id") != task.id]
                repos.executions.update(execution_id, {"tool_calls": tool_calls, "tool_results": tool_results, "verification_evidence": verification, "errors": errors, "pending_tasks": pending, "current_task": None})
                # stop on failure (can be retried/resumed)
                report = self._build_report(repos, execution_id, final_status="failed")
                repos.executions.update(execution_id, {"status": "failed", "final_report": report})
                self._persist_checkpoint(repos, execution_id, "failed")
                break
        return self.get_status(execution_id, repos=repos)

    def _build_report(self, repos: Repositories, execution_id: str, final_status: str) -> str:
        ex = repos.executions.get(execution_id)
        tasks = repos.tasks.get_by_execution(execution_id)
        done = [t for t in tasks if t.status == "completed"]
        failed = [t for t in tasks if t.status == "failed"]
        blocked = [t for t in tasks if t.status == "blocked"]
        pending = [t for t in tasks if t.status in ("pending", "in_progress")]
        lines = [
            f"Objective: {ex.user_objective if ex else ''}",
            f"Status: {final_status}",
            f"Tasks: {len(done)} completed, {len(failed)} failed, {len(blocked)} blocked, {len(pending)} pending.",
        ]
        if done:
            lines.append("Completed: " + "; ".join(t.title for t in done))
        if failed:
            lines.append("Failed: " + "; ".join(t.title for t in failed))
        if blocked:
            lines.append("Blocked: " + "; ".join(t.title for t in blocked))
        if ex and ex.errors:
            lines.append(f"Errors recorded: {len(ex.errors)}")
        return "\n".join(lines)

    # --- status / control ---
    def get_status(self, execution_id: str, repos: Optional[Repositories] = None) -> Dict[str, Any]:
        own = False
        if repos is None:
            db, repos = self._db(); own = True
        try:
            ex = repos.executions.get(execution_id)
            if not ex:
                return {"error": "Execution not found"}
            tasks = repos.tasks.get_by_execution(execution_id)
            return {
                "id": ex.id,
                "agent_id": ex.agent_id,
                "user_objective": ex.user_objective,
                "status": ex.status,
                "current_task": ex.current_task,
                "plan_version": ex.plan_version,
                "tasks": [
                    {"id": t.id, "title": t.title, "status": t.status, "dependencies": t.dependencies or [], "description": t.description, "expected_result": t.expected_result}
                    for t in tasks
                ],
                "completed_tasks": ex.completed_tasks or [],
                "pending_tasks": ex.pending_tasks or [],
                "tool_calls": ex.tool_calls or [],
                "tool_results": ex.tool_results or [],
                "errors": ex.errors or [],
                "checkpoints": ex.checkpoints or [],
                "approvals": ex.approvals or [],
                "verification_evidence": ex.verification_evidence or [],
                "final_report": ex.final_report,
                "created_at": ex.created_at.isoformat() if ex.created_at else None,
                "updated_at": ex.updated_at.isoformat() if ex.updated_at else None,
            }
        finally:
            if own:
                repos.db.close()

    def pause(self, execution_id: str) -> Dict[str, Any]:
        db, repos = self._db()
        try:
            ex = repos.executions.get(execution_id)
            if not ex: return {"error": "Execution not found"}
            if ex.status in TERMINAL: return self.get_status(execution_id, repos=repos)
            repos.executions.update(execution_id, {"status": "paused"})
            self._persist_checkpoint(repos, execution_id, "paused")
            return self.get_status(execution_id, repos=repos)
        finally:
            db.close()

    def stop(self, execution_id: str) -> Dict[str, Any]:
        db, repos = self._db()
        try:
            ex = repos.executions.get(execution_id)
            if not ex: return {"error": "Execution not found"}
            repos.executions.update(execution_id, {"status": "stopped", "current_task": None, "final_report": self._build_report(repos, execution_id, "stopped")})
            self._persist_checkpoint(repos, execution_id, "stopped")
            return self.get_status(execution_id, repos=repos)
        finally:
            db.close()

    def resume(self, execution_id: str) -> Dict[str, Any]:
        db, repos = self._db()
        try:
            ex = repos.executions.get(execution_id)
            if not ex: return {"error": "Execution not found"}
            if ex.status not in ("paused", "failed", "blocked", "pending", "running"):
                return self.get_status(execution_id, repos=repos)
            # reconstruct context: if running but interrupted, treat as paused resume
            repos.executions.update(execution_id, {"status": "running"})
            self._persist_checkpoint(repos, execution_id, "resumed")
            return self._run_loop(repos, execution_id)
        finally:
            db.close()

    def retry(self, execution_id: str, task_id: Optional[str] = None) -> Dict[str, Any]:
        db, repos = self._db()
        try:
            ex = repos.executions.get(execution_id)
            if not ex: return {"error": "Execution not found"}
            todo = TodoManager(repos)
            if task_id:
                todo.retry_task(task_id)
            else:
                for t in todo.list_tasks(execution_id):
                    if t.status in ("failed", "blocked"):
                        todo.retry_task(t.id)
            repos.executions.update(execution_id, {"status": "running", "final_report": None})
            self._persist_checkpoint(repos, execution_id, "retry")
            return self._run_loop(repos, execution_id)
        finally:
            db.close()

    def create_checkpoint(self, execution_id: str, label: str = "manual") -> Dict[str, Any]:
        db, repos = self._db()
        try:
            cp = self._persist_checkpoint(repos, execution_id, label)
            return self.get_status(execution_id, repos=repos)
        finally:
            db.close()


execution_engine = ExecutionEngine()
