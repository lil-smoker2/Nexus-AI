"""Computer Automation MCP server: session/app/window inspection primitives."""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
from typing import Any, Dict

from app.mcp.base import BaseMcpServer, McpServerConfig, ToolDefinition, ToolResult


class ComputerAutomationMcpServer(BaseMcpServer):
    server_type = "computer"

    def __init__(self, config: McpServerConfig):
        super().__init__(config)
        self._register_tools()

    def _register_tools(self) -> None:
        t = self.register_tool
        t(ToolDefinition("computer.get_session_info", "Get OS and session info", {"type":"object","properties":{}}, "read"), self.get_session_info)
        t(ToolDefinition("computer.list_processes", "List running processes (top)", {"type":"object","properties":{"limit":{"type":"integer"}}}, "read"), self.list_processes)
        t(ToolDefinition("computer.which", "Locate an executable", {"type":"object","properties":{"name":{"type":"string"}},"required":["name"]}, "read"), self.which)
        t(ToolDefinition("computer.open_path", "Open a path with xdg-open (gated)", {"type":"object","properties":{"path":{"type":"string"}},"required":["path"]}, "execute"), self.open_path)

    def get_session_info(self, args: Dict[str, Any]) -> ToolResult:
        info = {
            "platform": platform.platform(),
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
            "python": platform.python_version(),
            "cwd": os.getcwd(),
            "user": os.getenv("USER") or os.getenv("USERNAME"),
            "desktop": os.getenv("XDG_CURRENT_DESKTOP"),
            "session_type": os.getenv("XDG_SESSION_TYPE"),
            "display": os.getenv("DISPLAY"),
            "wayland_display": os.getenv("WAYLAND_DISPLAY"),
        }
        return ToolResult(success=True, content=info)

    def list_processes(self, args: Dict[str, Any]) -> ToolResult:
        limit = int(args.get("limit", 30))
        try:
            proc = subprocess.run(["ps", "-eo", "pid,comm,%cpu,%mem", "--sort=-%cpu"], capture_output=True, text=True, timeout=10)
            if proc.returncode != 0:
                return ToolResult(success=False, error=proc.stderr.strip() or "ps failed")
            lines = proc.stdout.strip().splitlines()
            head = lines[:1]
            body = lines[1: 1 + max(1, min(limit, 200))]
            return ToolResult(success=True, content={"header": head[0] if head else "", "processes": body, "count": len(body)})
        except Exception as e:
            return ToolResult(success=False, error=str(e))

    def which(self, args: Dict[str, Any]) -> ToolResult:
        name = str(args.get("name", "")).strip()
        if not name:
            return ToolResult(success=False, error="name is required")
        path = shutil.which(name)
        return ToolResult(success=True, content={"name": name, "path": path, "found": path is not None})

    def open_path(self, args: Dict[str, Any]) -> ToolResult:
        path = str(args.get("path", "")).strip()
        if not path:
            return ToolResult(success=False, error="path is required")
        opener = shutil.which("xdg-open")
        if not opener:
            return ToolResult(success=False, error="xdg-open not available in this environment")
        try:
            # Non-blocking open
            subprocess.Popen([opener, path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return ToolResult(success=True, content={"path": path, "opened": True})
        except Exception as e:
            return ToolResult(success=False, error=str(e))
