"""Git MCP server: repository inspection and controlled operations."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.mcp.base import BaseMcpServer, McpServerConfig, ToolDefinition, ToolResult


class GitMcpServer(BaseMcpServer):
    server_type = "git"

    def __init__(self, config: McpServerConfig):
        super().__init__(config)
        cfg = config.config or {}
        root = (config.args[0] if config.args else None) or cfg.get("root") or config.env.get("ROOT") or os.getcwd()
        self.root = Path(root).resolve()
        self.allow_mutating = bool(cfg.get("allow_mutating", False))
        self._register_tools()

    def _run(self, cmd: List[str], cwd: Optional[Path] = None, timeout: int = 30) -> ToolResult:
        try:
            p = cwd or self.root
            proc = subprocess.run(cmd, cwd=str(p), capture_output=True, text=True, timeout=timeout)
            ok = proc.returncode == 0
            return ToolResult(success=ok, content={
                "cmd": cmd, "cwd": str(p), "exit_code": proc.returncode,
                "stdout": (proc.stdout or "")[-200000:], "stderr": (proc.stderr or "")[-200000:],
            }, error=None if ok else ((proc.stderr or "").strip() or f"Exit {proc.returncode}"))
        except Exception as e:
            return ToolResult(success=False, error=str(e))

    def _register_tools(self) -> None:
        t = self.register_tool
        # read ops
        t(ToolDefinition("git.status", "Show git status", {"type":"object","properties":{"path":{"type":"string"}}}, "read"), self.status)
        t(ToolDefinition("git.diff", "Show git diff", {"type":"object","properties":{"staged":{"type":"boolean"},"pathspec":{"type":"string"},"ref":{"type":"string"}}}, "read"), self.diff)
        t(ToolDefinition("git.log", "Show git log", {"type":"object","properties":{"limit":{"type":"integer"},"ref":{"type":"string"}}}, "read"), self.log)
        t(ToolDefinition("git.branch_list", "List branches", {"type":"object","properties":{}}, "read"), self.branch_list)
        t(ToolDefinition("git.current_branch", "Show current branch", {"type":"object","properties":{}}, "read"), self.current_branch)
        t(ToolDefinition("git.show", "Show commit/object", {"type":"object","properties":{"ref":{"type":"string"}},"required":["ref"]}, "read"), self.show)
        t(ToolDefinition("git.remote_list", "List remotes", {"type":"object","properties":{}}, "read"), self.remote_list)
        # gated mutating ops
        t(ToolDefinition("git.add", "Stage files (gated)", {"type":"object","properties":{"paths":{"type":"array","items":{"type":"string"}}},"required":["paths"]}, "write"), self.add)
        t(ToolDefinition("git.commit", "Create commit (gated)", {"type":"object","properties":{"message":{"type":"string"}},"required":["message"]}, "write"), self.commit)
        t(ToolDefinition("git.create_branch", "Create/switch branch (gated)", {"type":"object","properties":{"name":{"type":"string"},"checkout":{"type":"boolean"}},"required":["name"]}, "write"), self.create_branch)

    def status(self, args: Dict[str, Any]) -> ToolResult:
        return self._run(["git", "status", "--short", "--branch"])

    def diff(self, args: Dict[str, Any]) -> ToolResult:
        cmd = ["git", "diff"]
        if args.get("staged"):
            cmd.append("--staged")
        if args.get("ref"):
            cmd.append(str(args["ref"]))
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

    def remote_list(self, args: Dict[str, Any]) -> ToolResult:
        return self._run(["git", "remote", "-v"])

    def _require_mutating(self) -> Optional[ToolResult]:
        if not self.allow_mutating:
            return ToolResult(success=False, error="Mutating git operations are disabled by policy (enable allow_mutating to permit gated operations)")
        return None

    def add(self, args: Dict[str, Any]) -> ToolResult:
        gated = self._require_mutating()
        if gated: return gated
        paths = args.get("paths") or []
        if not isinstance(paths, list) or not paths:
            return ToolResult(success=False, error="paths (non-empty array) is required")
        cmd = ["git", "add", "--"] + [str(p) for p in paths]
        return self._run(cmd)

    def commit(self, args: Dict[str, Any]) -> ToolResult:
        gated = self._require_mutating()
        if gated: return gated
        msg = str(args.get("message") or "").strip()
        if not msg:
            return ToolResult(success=False, error="message is required")
        return self._run(["git", "commit", "-m", msg])

    def create_branch(self, args: Dict[str, Any]) -> ToolResult:
        gated = self._require_mutating()
        if gated: return gated
        name = str(args.get("name") or "").strip()
        if not name:
            return ToolResult(success=False, error="name is required")
        checkout = bool(args.get("checkout", True))
        if checkout:
            return self._run(["git", "checkout", "-b", name])
        return self._run(["git", "branch", name])
