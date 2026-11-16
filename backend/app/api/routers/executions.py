"""Executions API router."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Any, Dict, List, Optional
from datetime import datetime
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.database.repositories.container import Repositories
from app.agents.base import AgentType

router = APIRouter()


def get_repos(db: Session = Depends(get_db)) -> Repositories:
    return Repositories(db)


class CreateExecutionRequest(BaseModel):
    agent_id: AgentType
    user_objective: str
    conversation_id: Optional[str] = None


class ExecutionResponse(BaseModel):
    id: str
    agent_id: str
    user_objective: str
    status: str
    current_task: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


@router.post("", response_model=ExecutionResponse)
async def create_execution(
    request: CreateExecutionRequest,
    repos: Repositories = Depends(get_repos),
):
    execution = repos.executions.create_execution(
        agent_id=request.agent_id.value,
        user_objective=request.user_objective,
        conversation_id=request.conversation_id,
    )
    return execution


@router.get("", response_model=List[ExecutionResponse])
async def list_executions(
    agent_id: Optional[str] = None,
    repos: Repositories = Depends(get_repos),
):
    if agent_id:
        return repos.executions.get_by_agent(agent_id)
    return repos.executions.list()


@router.get("/{execution_id}", response_model=ExecutionResponse)
async def get_execution(
    execution_id: str,
    repos: Repositories = Depends(get_repos),
):
    execution = repos.executions.get(execution_id)
    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")
    return execution
