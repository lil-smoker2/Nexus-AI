"""MCP management API router."""

from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.mcp.manager import mcp_manager

router = APIRouter()


class ToolCallRequest(BaseModel):
    tool: str
    arguments: Dict[str, Any] = {}


@router.get("/servers")
async def list_servers():
    return {"servers": mcp_manager.list_servers()}


@router.get("/servers/{server_id}")
async def get_server(server_id: str):
    s = mcp_manager.get_server(server_id)
    if not s:
        raise HTTPException(status_code=404, detail="Server not found")
    return s


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


@router.get("/servers/{server_id}/tools")
async def list_server_tools(server_id: str):
    s = mcp_manager.get_server(server_id)
    if not s:
        raise HTTPException(status_code=404, detail="Server not found")
    return {"server_id": server_id, "tools": mcp_manager.list_tools(server_id)}


@router.post("/servers/{server_id}/tools/call")
async def call_tool(server_id: str, req: ToolCallRequest):
    try:
        result = mcp_manager.call_tool(server_id, req.tool, req.arguments)
        if not result.get("success"):
            # still return structured result but mark error in payload
            return result
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/tools")
async def list_all_tools():
    return {"tools": mcp_manager.list_tools()}


@router.get("/audit")
async def audit(limit: int = 100):
    return {"events": mcp_manager.audit_log(limit=limit)}
