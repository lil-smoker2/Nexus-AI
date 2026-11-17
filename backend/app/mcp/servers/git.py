"""Git MCP server: repository inspection and controlled operations."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Any, Dict, List

from app.mcp.base import BaseMcpServer, McpServerConfig, ToolDefinition, ToolResult


class GitMcpServer(BaseMcpServer):
    server_type = "git"

    def __init__(self, config: McpServerConfig):
        super().__init__(config)
        root = (config.args[0] if config.args else None) or config.env.get("ROOT") or os.getcwd()
        self.root = Path(root).resolve()
        self._register_tools()

    def _run(self, cmd: List[str], cwd: Path | None = None) -> ToolResult:
        try:
            p = cwd or self.root
            proc = subprocess.run(cmd, cwd=str(p), capture_output=True, text=True, timeout=30)
            ok = proc.returncode == 0
            return ToolResult(success=ok, content={
                "cmd": cmd, "cwd": str(p), "exit_code": proc.returncode,
                "stdout": proc.stdout[-200000:], "stderr": proc.stderr[-200000:],
            }, error=None if ok else (proc.stderr.strip() or f"Exit {proc.returncode}"))
        except Exception as e:
            return ToolResult(success=False, error=str(e))

    def _register_tools(self) -> None:
        t = self.register_tool
        t(ToolDefinition("git.status", "Show git status", {"type":"object","properties":{"path":{"type":"string"}}}, "read"), self.status)
        t(ToolDefinition("git.diff", "Show git diff", {"type":"object","properties":{"staged":{"type":"boolean"},"pathspec":{"type":"string"}}}, "read"), self.diff)
        t(ToolDefinition("git.log", "Show git log", {"type":"object","properties":{"limit":{"type":"integer"},"ref":{"type":"string"}}}, "read"), self.log)
        t(ToolDefinition("git.branch_list", "List branches", {"type":"object","properties":{}}, "read"), self.branch_list)
        t(ToolDefinition("git.current_branch", "Show current branch", {"type":"object","properties":{}}, "read"), self.current_branch)
        t(ToolDefinition("git.show", "Show commit/object", {"type":"object","properties":{"ref":{"type":"string"}},"required":["ref"]}, "read"), self.show)

    def status(self, args: Dict[str, Any]) -> ToolResult:
        return self._run(["git", "status", "--short", "--branch"])
    def diff(self, args: Dict[str, Any]) -> ToolResult:
        cmd = ["git", "diff"]
        if args.get("staged"):
            cmd.append("--staged")
        if args.get("pathspec"):
            cmd.extend(["--", str(args["pathspec"])])
        return self._run(cmd)
    def log(self, args: Dict[str, Any]) -> ToolResult:
        limit = int(args.get("limit", 10))
        ref = str(args.get("ref", ""))
        cmd = ["git", "log", f"-{max(1, min(limit,100))}", "--oneline", "--decorate"]
        if ref:
            cmd.append(ref)
        return self._run(cmd)
    def branch_list(self, args: Dict[str, Any]) -> ToolResult:
        return self._run(["git", "branch", "-a", "-v"])
    def current_branch(self, args: Dict[str, Any]) -> ToolResult:
        return self._run(["git", "rev-parse", "--abbrev-ref", "HEAD"])
    def show(self, args: Dict[str, Any]) -> ToolResult:
        ref = str(args.get("ref", "HEAD"))
        return self._run(["git", "show", "--name-only", "--oneline", ref])
