"""Terminal MCP server: controlled command execution."""

from __future__ import annotations

import os
import re
import shlex
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.mcp.base import BaseMcpServer, McpServerConfig, ToolDefinition, ToolResult


DEFAULT_DENY_PATTERNS = [
    r"\brm\s+-rf\s+/(?:\s|$)",
    r"\bshutdown\b",
    r"\breboot\b",
    r"\bpoweroff\b",
    r"\bmkfs\b",
    r"\bdd\s+if=",
    r":\(\)\s*\{",  # fork bomb
]


class TerminalMcpServer(BaseMcpServer):
    server_type = "terminal"

    def __init__(self, config: McpServerConfig):
        super().__init__(config)
        cfg = config.config or {}
        root = (config.args[0] if config.args else None) or cfg.get("root") or config.env.get("ROOT") or os.getcwd()
        self.root = Path(root).resolve()
        self.max_output = int(cfg.get("max_output") or 200000)
        self.default_timeout_ms = int(cfg.get("timeout_ms") or config.timeout_ms or 30000)
        self.allow_patterns = [re.compile(p) for p in (cfg.get("allow_patterns") or [])]
        self.deny_patterns = [re.compile(p) for p in (cfg.get("deny_patterns") or DEFAULT_DENY_PATTERNS)]
        self._register_tools()

    def _register_tools(self) -> None:
        t = self.register_tool
        t(ToolDefinition("terminal.execute", "Execute a command in allowed working directory", {"type":"object","properties":{"command":{"type":"string"},"cwd":{"type":"string"},"timeout_ms":{"type":"integer"},"env":{"type":"object"}},"required":["command"]}, "execute"), self.execute)
        t(ToolDefinition("terminal.get_cwd", "Get default working directory", {"type":"object","properties":{}}, "read"), self.get_cwd)
        t(ToolDefinition("terminal.list_processes", "List running processes (top)", {"type":"object","properties":{"limit":{"type":"integer"}}}, "read"), self.list_processes)

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

    def _check_command_policy(self, cmd: str) -> Optional[str]:
        for pat in self.deny_patterns:
            if pat.search(cmd):
                return "Command denied by policy"
        if self.allow_patterns:
            if not any(p.search(cmd) for p in self.allow_patterns):
                return "Command not in allowlist"
        return None

    def execute(self, args: Dict[str, Any]) -> ToolResult:
        cmd = str(args.get("command", "")).strip()
        if not cmd:
            return ToolResult(success=False, error="command is required")
        denied = self._check_command_policy(cmd)
        if denied:
            return ToolResult(success=False, error=denied, content={"command": cmd, "denied": True})
        timeout_ms = int(args.get("timeout_ms", self.default_timeout_ms))
        timeout = max(1, timeout_ms / 1000.0)
        try:
            cwd = self._cwd(args)
            env = os.environ.copy()
            extra_env = args.get("env") or {}
            if isinstance(extra_env, dict):
                for k, v in extra_env.items():
                    env[str(k)] = str(v)
            start = time.time()
            proc = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True, timeout=timeout, env=env)
            duration = int((time.time() - start) * 1000)
            stdout = (proc.stdout or "")[-self.max_output:]
            stderr = (proc.stderr or "")[-self.max_output:]
            return ToolResult(success=proc.returncode == 0, content={
                "command": cmd, "cwd": cwd, "exit_code": proc.returncode,
                "stdout": stdout, "stderr": stderr, "duration_ms": duration,
                "truncated": (len(proc.stdout or "") > self.max_output) or (len(proc.stderr or "") > self.max_output),
            }, error=None if proc.returncode == 0 else f"Exit code {proc.returncode}")
        except subprocess.TimeoutExpired as e:
            out = (e.stdout or "")
            err = (e.stderr or "")
            if isinstance(out, bytes):
                out = out.decode("utf-8", errors="replace")
            if isinstance(err, bytes):
                err = err.decode("utf-8", errors="replace")
            return ToolResult(success=False, error=f"Timed out after {timeout}s", content={"stdout": out[-self.max_output:], "stderr": err[-self.max_output:], "timeout": True})
        except Exception as e:
            return ToolResult(success=False, error=str(e))

    def get_cwd(self, args: Dict[str, Any]) -> ToolResult:
        return ToolResult(success=True, content={"cwd": str(self.root)})

    def list_processes(self, args: Dict[str, Any]) -> ToolResult:
        limit = int(args.get("limit", 30))
        try:
            proc = subprocess.run(["ps", "-eo", "pid,ppid,comm,%cpu,%mem,etime", "--sort=-%cpu"], capture_output=True, text=True, timeout=10)
            if proc.returncode != 0:
                return ToolResult(success=False, error=proc.stderr.strip() or "ps failed")
            lines = proc.stdout.strip().splitlines()
            header = lines[:1]
            body = lines[1: 1 + max(1, min(limit, 200))]
            return ToolResult(success=True, content={"header": header[0] if header else "", "processes": body, "count": len(body)})
        except Exception as e:
            return ToolResult(success=False, error=str(e))
