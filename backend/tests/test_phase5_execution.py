"""Phase 5 tests: planning, TODOs, dependencies, execution loop, recovery."""

import os
import shutil
from pathlib import Path

from app.database.session import init_db, SessionLocal
from app.database.repositories.container import Repositories
from app.execution.planner import TaskPlanner
from app.execution.engine import execution_engine
from app.mcp.manager import mcp_manager, _default_root


REPO_ROOT = Path(_default_root())


def _cleanup(name: str):
    p = REPO_ROOT / name
    if p.exists():
        if p.is_dir():
            shutil.rmtree(p)
        else:
            p.unlink()


def setup_module(module=None):
    init_db()
    mcp_manager.initialize()


def teardown_module(module=None):
    try:
        mcp_manager.shutdown()
    except Exception:
        pass


def test_planner_creates_structured_tasks():
    planner = TaskPlanner()
    plan = planner.plan("Create a folder named demo_phase5 and 2 files inside it")
    assert plan.objective
    assert len(plan.tasks) >= 3
    t = plan.tasks[0]
    assert t.title and t.description and t.expected_result
    assert isinstance(t.dependencies, list)
    assert isinstance(t.required_tools, list)
    assert isinstance(t.completion_conditions, list)
    assert isinstance(t.risks, list)
    d = plan.to_dict()
    assert "tasks" in d and d["tasks"]


def test_execution_create_folder_and_files():
    folder = "demo_phase5_files"
    _cleanup(folder)
    result = execution_engine.create_and_run(
        objective=f"Create folder named {folder} and 3 files",
        agent_id="companion",
        auto_run=True,
    )
    assert result.get("status") == "completed", result
    p = REPO_ROOT / folder
    assert p.is_dir(), f"expected folder at {p}"
    files = [f for f in p.iterdir() if f.is_file()]
    assert len(files) >= 3
    assert result.get("final_report")
    assert result.get("verification_evidence")
    assert isinstance(result.get("tool_calls"), list) and result.get("tool_calls")
    assert isinstance(result.get("tool_results"), list) and result.get("tool_results")
    assert result.get("plan_version", 0) >= 1
    _cleanup(folder)


def test_task_dependencies_ordering():
    folder = "demo_phase5_dep"
    _cleanup(folder)
    result = execution_engine.create_and_run(
        objective=f"Create folder named {folder} and 2 files",
        agent_id="companion",
        auto_run=True,
    )
    assert result["status"] == "completed", result
    tasks = result.get("tasks", [])
    assert tasks
    assert isinstance(tasks[0]["dependencies"], list)
    assert all(t["status"] == "completed" for t in tasks)
    assert any(t["dependencies"] for t in tasks[1:])
    _cleanup(folder)


def test_todo_manager_crud_and_status_ops():
    db = SessionLocal()
    repos = Repositories(db)
    try:
        ex = repos.executions.create_execution("companion", "todo test")
        t = repos.tasks.create({"execution_id": ex.id, "title": "T1", "status": "pending", "dependencies": []})
        assert t.id
        got = repos.tasks.get(t.id)
        assert got and got.title == "T1"
        upd = repos.tasks.update(t.id, {"status": "in_progress"})
        assert upd.status == "in_progress"
        done = repos.tasks.update(t.id, {"status": "completed"})
        assert done.status == "completed"
        reopened = repos.tasks.update(t.id, {"status": "pending"})
        assert reopened.status == "pending"
        blocked = repos.tasks.update(t.id, {"status": "blocked", "risks": ["blocked: test"]})
        assert blocked.status == "blocked"
        retried = repos.tasks.update(t.id, {"status": "pending"})
        assert retried.status == "pending"
        ok = repos.tasks.delete(t.id)
        assert ok is True
        assert repos.tasks.get(t.id) is None
    finally:
        db.close()


def test_pause_resume_stop_and_checkpoint():
    folder = "demo_phase5_pause"
    _cleanup(folder)
    result = execution_engine.create_and_run(
        objective=f"Create folder named {folder} and 2 files",
        agent_id="companion",
        auto_run=False,
    )
    ex_id = result["id"]
    cp = execution_engine.create_checkpoint(ex_id, label="manual-test")
    assert cp.get("checkpoints")

    stopped = execution_engine.stop(ex_id)
    assert stopped["status"] == "stopped"
    assert stopped.get("final_report")

    result2 = execution_engine.create_and_run(
        objective=f"Create folder named {folder} and 1 files",
        agent_id="companion",
        auto_run=False,
    )
    ex2 = result2["id"]
    paused = execution_engine.pause(ex2)
    assert paused["status"] == "paused"
    resumed = execution_engine.resume(ex2)
    assert resumed["status"] in ("completed", "failed", "blocked", "stopped")
    _cleanup(folder)


def test_execution_status_and_history_fields():
    folder = "demo_phase5_hist"
    _cleanup(folder)
    result = execution_engine.create_and_run(
        objective=f"Create folder named {folder} and 1 files",
        agent_id="companion",
        auto_run=True,
    )
    ex_id = result["id"]
    status = execution_engine.get_status(ex_id)
    assert status["id"] == ex_id
    for key in [
        "tasks", "tool_calls", "tool_results", "errors", "checkpoints",
        "verification_evidence", "final_report", "completed_tasks", "pending_tasks",
    ]:
        assert key in status
    assert status["final_report"]
    assert status.get("plan_version", 0) >= 1
    _cleanup(folder)


def test_build_app_workflow():
    app_dir = "sample_app"
    _cleanup(app_dir)
    result = execution_engine.create_and_run(
        objective="Build a small Python application",
        agent_id="companion",
        auto_run=True,
    )
    assert result.get("status") == "completed", result
    assert (REPO_ROOT / app_dir / "main.py").is_file()
    _cleanup(app_dir)
