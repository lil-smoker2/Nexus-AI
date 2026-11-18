"""MCP management API router."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.mcp.manager import mcp_manager

router = APIRouter()


class ToolCallRequest(BaseModel):
    tool: str
    arguments: Dict[str, Any] = Field(default_factory=dict)


class ServerRegisterRequest(BaseModel):
    name: str
    description: Optional[str] = ""
    transport: str = "internal"  # internal | stdio | streamable_http | http
    endpoint: str
    args: List[Any] = Field(default_factory=list)
    env: Dict[str, Any] = Field(default_factory=dict)
    auth_config: Dict[str, Any] = Field(default_factory=dict)
    config: Dict[str, Any] = Field(default_factory=dict)
    permissions: Dict[str, Any] = Field(default_factory=dict)
    enabled: bool = True


class ServerUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    transport: Optional[str] = None
    endpoint: Optional[str] = None
    args: Optional[List[Any]] = None
    env: Optional[Dict[str, Any]] = None
    auth_config: Optional[Dict[str, Any]] = None
    config: Optional[Dict[str, Any]] = None
    permissions: Optional[Dict[str, Any]] = None
    enabled: Optional[bool] = None


@router.get("/servers")
async def list_servers():
    return {"servers": mcp_manager.list_servers()}


@router.post("/servers")
async def register_server(req: ServerRegisterRequest):
    try:
        server = mcp_manager.register_server(req.model_dump())
        return {"server": server}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/servers/{server_id}")
async def get_server(server_id: str):
    s = mcp_manager.get_server(server_id)
    if not s:
        raise HTTPException(status_code=404, detail="Server not found")
    return s


@router.patch("/servers/{server_id}")
async def update_server(server_id: str, req: ServerUpdateRequest):
    try:
        data = {k: v for k, v in req.model_dump().items() if v is not None}
        server = mcp_manager.update_server(server_id, data)
        if not server:
            raise HTTPException(status_code=404, detail="Server not found")
        return {"server": server}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/servers/{server_id}")
async def delete_server(server_id: str):
    try:
        return mcp_manager.delete_server(server_id)
    except Exception as e:
        msg = str(e)
        code = 404 if "not found" in msg.lower() else 400
        raise HTTPException(status_code=code, detail=msg)


@router.post("/servers/{server_id}/connect")
async def connect_server(server_id: str):
    try:
        return mcp_manager.connect(server_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/servers/{server_id}/disconnect")
async def disconnect_server(server_id: str):
    try:
        return mcp_manager.disconnect(server_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/servers/{server_id}/restart")
async def restart_server(server_id: str):
    try:
        return mcp_manager.restart(server_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/servers/{server_id}/health")
async def server_health(server_id: str):
    s = mcp_manager.get_server(server_id)
    if not s:
        raise HTTPException(status_code=404, detail="Server not found")
    return mcp_manager.health(server_id)


@router.get("/servers/{server_id}/tools")
async def list_server_tools(server_id: str):
    s = mcp_manager.get_server(server_id)
    if not s:
        raise HTTPException(status_code=404, detail="Server not found")
    return {"server_id": server_id, "tools": mcp_manager.list_tools(server_id)}


@router.get("/servers/{server_id}/resources")
async def list_server_resources(server_id: str):
    s = mcp_manager.get_server(server_id)
    if not s:
        raise HTTPException(status_code=404, detail="Server not found")
    return {"server_id": server_id, "resources": mcp_manager.list_resources(server_id)}


@router.get("/servers/{server_id}/prompts")
async def list_server_prompts(server_id: str):
    s = mcp_manager.get_server(server_id)
    if not s:
        raise HTTPException(status_code=404, detail="Server not found")
    return {"server_id": server_id, "prompts": mcp_manager.list_prompts(server_id)}


@router.post("/servers/{server_id}/tools/call")
async def call_tool(server_id: str, req: ToolCallRequest):
    try:
        result = mcp_manager.call_tool(server_id, req.tool, req.arguments)
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/tools")
async def list_all_tools():
    return {"tools": mcp_manager.list_tools()}


@router.get("/resources")
async def list_all_resources():
    return {"resources": mcp_manager.list_resources()}


@router.get("/prompts")
async def list_all_prompts():
    return {"prompts": mcp_manager.list_prompts()}


@router.get("/audit")
async def audit(limit: int = Query(100, ge=1, le=1000), server_id: Optional[str] = None):
    return {"events": mcp_manager.audit_log(limit=limit, server_id=server_id)}
