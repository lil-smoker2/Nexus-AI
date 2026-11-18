"""Executions API router (Phase 5: planning/execution engine)."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Any, Dict, List, Optional
from datetime import datetime
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.database.repositories.container import Repositories
from app.agents.base import AgentType
from app.execution.engine import execution_engine

router = APIRouter()


def get_repos(db: Session = Depends(get_db)) -> Repositories:
    return Repositories(db)


class CreateExecutionRequest(BaseModel):
    agent_id: AgentType = AgentType.COMPANION
    user_objective: str
    conversation_id: Optional[str] = None
    auto_run: bool = True


class ExecutionResponse(BaseModel):
    id: str
    agent_id: str
    user_objective: str
    status: str
    current_task: Optional[str] = None
    plan_version: Optional[int] = 0
    final_report: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


@router.post("")
async def create_execution(
    request: CreateExecutionRequest,
):
    # plan and (optionally) run via execution engine
    result = execution_engine.create_and_run(
        objective=request.user_objective,
        agent_id=request.agent_id.value if isinstance(request.agent_id, AgentType) else str(request.agent_id),
        conversation_id=request.conversation_id,
        auto_run=request.auto_run,
    )
    if result.get("error"):
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.get("")
async def list_executions(
    agent_id: Optional[str] = None,
    repos: Repositories = Depends(get_repos),
):
    if agent_id:
        rows = repos.executions.get_by_agent(agent_id)
    else:
        rows = repos.executions.list()
    return [
        {
            "id": e.id,
            "agent_id": e.agent_id,
            "user_objective": e.user_objective,
            "status": e.status,
            "current_task": e.current_task,
            "plan_version": e.plan_version,
            "final_report": e.final_report,
            "created_at": e.created_at,
            "updated_at": e.updated_at,
        }
        for e in rows
    ]


@router.get("/{execution_id}")
async def get_execution(execution_id: str):
    result = execution_engine.get_status(execution_id)
    if result.get("error"):
        raise HTTPException(status_code=404, detail="Execution not found")
    return result


@router.post("/{execution_id}/pause")
async def pause_execution(execution_id: str):
    result = execution_engine.pause(execution_id)
    if result.get("error"):
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.post("/{execution_id}/resume")
async def resume_execution(execution_id: str):
    result = execution_engine.resume(execution_id)
    if result.get("error"):
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.post("/{execution_id}/stop")
async def stop_execution(execution_id: str):
    result = execution_engine.stop(execution_id)
    if result.get("error"):
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.post("/{execution_id}/retry")
async def retry_execution(execution_id: str, task_id: Optional[str] = None):
    result = execution_engine.retry(execution_id, task_id=task_id)
    if result.get("error"):
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.post("/{execution_id}/checkpoint")
async def checkpoint_execution(execution_id: str, label: str = "manual"):
    result = execution_engine.create_checkpoint(execution_id, label=label)
    if result.get("error"):
        raise HTTPException(status_code=404, detail=result["error"])
    return result
