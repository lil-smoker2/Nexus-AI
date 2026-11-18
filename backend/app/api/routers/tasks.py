"""Tasks/TODO API router (Phase 5)."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.database.repositories.container import Repositories

router = APIRouter()


def get_repos(db: Session = Depends(get_db)) -> Repositories:
    return Repositories(db)


class TaskCreate(BaseModel):
    execution_id: Optional[str] = None
    title: str
    description: Optional[str] = None
    expected_result: Optional[str] = None
    status: str = "pending"
    required_tools: List[Any] = []
    completion_conditions: List[Any] = []
    risks: List[Any] = []
    dependencies: List[str] = []
    parent_task_id: Optional[str] = None


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    expected_result: Optional[str] = None
    status: Optional[str] = None
    required_tools: Optional[List[Any]] = None
    completion_conditions: Optional[List[Any]] = None
    risks: Optional[List[Any]] = None
    dependencies: Optional[List[str]] = None
    parent_task_id: Optional[str] = None


class TaskOut(BaseModel):
    id: str
    execution_id: Optional[str] = None
    parent_task_id: Optional[str] = None
    title: str
    description: Optional[str] = None
    expected_result: Optional[str] = None
    status: str
    required_tools: Optional[List[Any]] = None
    completion_conditions: Optional[List[Any]] = None
    risks: Optional[List[Any]] = None
    dependencies: Optional[List[str]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


@router.get("", response_model=List[TaskOut])
def list_tasks(execution_id: Optional[str] = None, status: Optional[str] = None, repos: Repositories = Depends(get_repos)):
    if execution_id:
        return repos.tasks.get_by_execution(execution_id)
    if status:
        return repos.tasks.get_by_status(status)
    return repos.tasks.get_multi(limit=200)


@router.post("", response_model=TaskOut)
def create_task(payload: TaskCreate, repos: Repositories = Depends(get_repos)):
    data = payload.model_dump()
    return repos.tasks.create(data)


@router.get("/{task_id}", response_model=TaskOut)
def get_task(task_id: str, repos: Repositories = Depends(get_repos)):
    t = repos.tasks.get(task_id)
    if not t:
        raise HTTPException(status_code=404, detail="Task not found")
    return t


@router.patch("/{task_id}", response_model=TaskOut)
def update_task(task_id: str, payload: TaskUpdate, repos: Repositories = Depends(get_repos)):
    t = repos.tasks.get(task_id)
    if not t:
        raise HTTPException(status_code=404, detail="Task not found")
    updates = {k: v for k, v in payload.model_dump().items() if v is not None}
    return repos.tasks.update(task_id, updates)


@router.delete("/{task_id}")
def delete_task(task_id: str, repos: Repositories = Depends(get_repos)):
    ok = repos.tasks.delete(task_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"deleted": True, "id": task_id}


@router.post("/{task_id}/complete", response_model=TaskOut)
def complete_task(task_id: str, repos: Repositories = Depends(get_repos)):
    t = repos.tasks.update(task_id, {"status": "completed"})
    if not t:
        raise HTTPException(status_code=404, detail="Task not found")
    return t


@router.post("/{task_id}/reopen", response_model=TaskOut)
def reopen_task(task_id: str, repos: Repositories = Depends(get_repos)):
    t = repos.tasks.update(task_id, {"status": "pending"})
    if not t:
        raise HTTPException(status_code=404, detail="Task not found")
    return t


@router.post("/{task_id}/block", response_model=TaskOut)
def block_task(task_id: str, reason: Optional[str] = None, repos: Repositories = Depends(get_repos)):
    t = repos.tasks.get(task_id)
    if not t:
        raise HTTPException(status_code=404, detail="Task not found")
    risks = list(t.risks or [])
    if reason:
        risks.append(f"blocked: {reason}")
    t = repos.tasks.update(task_id, {"status": "blocked", "risks": risks})
    return t


@router.post("/{task_id}/retry", response_model=TaskOut)
def retry_task(task_id: str, repos: Repositories = Depends(get_repos)):
    t = repos.tasks.get(task_id)
    if not t:
        raise HTTPException(status_code=404, detail="Task not found")
    if t.status not in ("failed", "blocked"):
        return t
    t = repos.tasks.update(task_id, {"status": "pending"})
    return t
