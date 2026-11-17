"""Terminal MCP server: controlled command execution."""

from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path
from typing import Any, Dict

from app.mcp.base import BaseMcpServer, McpServerConfig, ToolDefinition, ToolResult


class TerminalMcpServer(BaseMcpServer):
    server_type = "terminal"

    def __init__(self, config: McpServerConfig):
        super().__init__(config)
        root = (config.args[0] if config.args else None) or config.env.get("ROOT") or os.getcwd()
        self.root = Path(root).resolve()
        self._register_tools()

    def _register_tools(self) -> None:
        t = self.register_tool
        t(ToolDefinition("terminal.execute", "Execute a command", {"type":"object","properties":{"command":{"type":"string"},"cwd":{"type":"string"},"timeout_ms":{"type":"integer"}},"required":["command"]}, "execute"), self.execute)
        t(ToolDefinition("terminal.get_cwd", "Get default working directory", {"type":"object","properties":{}}, "read"), self.get_cwd)

    def _cwd(self, args: Dict[str, Any]) -> str:
        cwd = args.get("cwd")
        if cwd:
            p = (self.root / cwd).resolve() if not os.path.isabs(cwd) else Path(cwd).resolve()
            try:
                p.relative_to(self.root)
            except Exception:
                if p != self.root:
                    raise ValueError("cwd escapes allowed root")
            return str(p)
        return str(self.root)

    def execute(self, args: Dict[str, Any]) -> ToolResult:
        cmd = str(args.get("command", "")).strip()
        if not cmd:
            return ToolResult(success=False, error="command is required")
        timeout_ms = int(args.get("timeout_ms", self.config.timeout_ms or 30000))
        timeout = max(1, timeout_ms / 1000.0)
        try:
            cwd = self._cwd(args)
            start = time.time()
            proc = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True, timeout=timeout)
            duration = int((time.time() - start) * 1000)
            return ToolResult(success=proc.returncode == 0, content={
                "command": cmd, "cwd": cwd, "exit_code": proc.returncode,
                "stdout": proc.stdout[-200000:], "stderr": proc.stderr[-200000:], "duration_ms": duration,
            }, error=None if proc.returncode == 0 else f"Exit code {proc.returncode}")
        except subprocess.TimeoutExpired as e:
            return ToolResult(success=False, error=f"Timed out after {timeout}s", content={"stdout": (e.stdout or "")[-100000:], "stderr": (e.stderr or "")[-100000:]})
        except Exception as e:
            return ToolResult(success=False, error=str(e))

    def get_cwd(self, args: Dict[str, Any]) -> ToolResult:
        return ToolResult(success=True, content={"cwd": str(self.root)})
