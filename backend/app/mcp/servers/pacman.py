"""Pacman adapter for Arch Linux package management.

Exposes structured read-only inspection/search plus privileged mutating
operations (install/remove/update) that are gated behind an explicit
authorization mechanism. No arbitrary sudo command execution is allowed:
mutating tools require both `approved=true` and a configured privilege
escalation command.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from typing import Any, Dict, List, Optional

from app.mcp.base import BaseMcpServer, McpServerConfig, ToolDefinition, ToolResult


DEFAULT_SUDO = ["sudo", "-n"]
MUTATING_PERMISSIONS = {"install", "remove", "update", "refresh"}


def _run(cmd: List[str], timeout: int = 120) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)


class PacmanMcpServer(BaseMcpServer):
    server_type = "pacman"

    def __init__(self, config: McpServerConfig):
        super().__init__(config)
        cfg = config.config or {}
        self.pacman_bin = cfg.get("pacman_bin") or shutil.which("pacman") or "pacman"
        self.sudo_prefix = list(cfg.get("sudo_prefix") or DEFAULT_SUDO)
        self.allow_mutating = bool(cfg.get("allow_mutating", False))
        self.max_results = int(cfg.get("max_results") or 100)
        self.timeout_seconds = int(cfg.get("timeout_seconds") or 120)
        self._register_tools()

    def _ok(self, content: Any = None, **meta: Any) -> ToolResult:
        return ToolResult(success=True, content=content, metadata=meta)

    def _err(self, msg: str) -> ToolResult:
        return ToolResult(success=False, error=msg)

    def _pacman_available(self) -> bool:
        return bool(shutil.which(self.pacman_bin))

    def _run_pacman(self, args: List[str], timeout: Optional[int] = None, privileged: bool = False) -> subprocess.CompletedProcess:
        cmd = list(self.sudo_prefix) + [self.pacman_bin] + args if privileged else [self.pacman_bin] + args
        return _run(cmd, timeout=timeout or self.timeout_seconds)

    def _register_tools(self) -> None:
        t = self.register_tool
        t(ToolDefinition("pacman.is_available", "Check whether pacman is available on this host", {"type": "object", "properties": {}}, "read"), self.is_available)
        t(ToolDefinition("pacman.search", "Search repositories by name/description", {"type": "object", "properties": {"query": {"type": "string"}, "limit": {"type": "integer"}}}, "read"), self.search)
        t(ToolDefinition("pacman.info", "Show package information (installed or sync)", {"type": "object", "properties": {"package": {"type": "string"}, "sync": {"type": "boolean"}}}, "read"), self.info)
        t(ToolDefinition("pacman.list_installed", "List installed packages (optionally filtered)", {"type": "object", "properties": {"query": {"type": "string"}, "limit": {"type": "integer"}}}, "read"), self.list_installed)
        t(ToolDefinition("pacman.list_files", "List files owned by an installed package", {"type": "object", "properties": {"package": {"type": "string"}}, "required": ["package"]}, "read"), self.list_files)
        t(ToolDefinition("pacman.dependencies", "Inspect dependencies of a package", {"type": "object", "properties": {"package": {"type": "string"}, "sync": {"type": "boolean"}}}, "read"), self.dependencies)
        t(ToolDefinition("pacman.updates", "Check for available system updates", {"type": "object", "properties": {"refresh": {"type": "boolean"}}}, "read"), self.updates)
        t(ToolDefinition("pacman.install", "Install package(s) (privileged; requires approved=true)", {"type": "object", "properties": {"packages": {"type": "array", "items": {"type": "string"}}, "refresh": {"type": "boolean"}, "approved": {"type": "boolean"}}, "required": ["packages"]}, "destructive"), self.install)
        t(ToolDefinition("pacman.remove", "Remove package(s) (privileged; requires approved=true)", {"type": "object", "properties": {"packages": {"type": "array", "items": {"type": "string"}}, "recursive": {"type": "boolean"}, "nosave": {"type": "boolean"}, "approved": {"type": "boolean"}}, "required": ["packages"]}, "destructive"), self.remove)
        t(ToolDefinition("pacman.update", "Run a system update (privileged; requires approved=true)", {"type": "object", "properties": {"refresh": {"type": "boolean"}, "approved": {"type": "boolean"}}, "required": []}, "destructive"), self.update)

    # ---- availability ----
    def is_available(self, args: Dict[str, Any]) -> ToolResult:
        path = shutil.which(self.pacman_bin)
        return self._ok({"available": bool(path), "pacman": path, "sudo": self.sudo_prefix, "allow_mutating": self.allow_mutating})

    # ---- read-only inspection ----
    def search(self, args: Dict[str, Any]) -> ToolResult:
        if not self._pacman_available():
            return self._err("pacman not available")
        query = str(args.get("query", "")).strip()
        if not query:
            return self._err("query is required")
        limit = max(1, min(int(args.get("limit", self.max_results)), self.max_results))
        proc = self._run_pacman(["-Ss", query])
        if proc.returncode != 0:
            return self._err(proc.stderr.strip() or "pacman -Ss failed")
        packages: List[Dict[str, str]] = []
        current: Optional[Dict[str, str]] = None
        for line in proc.stdout.splitlines():
            if not line.strip():
                continue
            if line.startswith(("repo/", "core/", "extra/", "community/", "multilib/")) or ("/" in line.split()[0] and not line.startswith(" ")):
                if current:
                    packages.append(current)
                if len(packages) >= limit:
                    break
                parts = line.split(None, 1)
                namever = parts[0]
                desc = parts[1] if len(parts) > 1 else ""
                if "/" in namever:
                    repo, nv = namever.split("/", 1)
                else:
                    repo, nv = "", namever
                if "-" in nv:
                    name, version = nv.rsplit("-", 2)[0], nv.rsplit("-", 2)[-1] if nv.count("-") >= 2 else nv
                else:
                    name, version = nv, ""
                current = {"repo": repo, "name": name, "version": version, "description": desc.strip()}
            elif current is not None:
                current.setdefault("detail", "")
                current["detail"] += line.strip() + " "
        if current and len(packages) < limit:
            packages.append(current)
        return self._ok({"query": query, "packages": packages, "count": len(packages)})

    def info(self, args: Dict[str, Any]) -> ToolResult:
        if not self._pacman_available():
            return self._err("pacman not available")
        package = str(args.get("package", "")).strip()
        if not package:
            return self._err("package is required")
        sync = bool(args.get("sync", False))
        proc = self._run_pacman(["-Si" if sync else "-Qi", package])
        if proc.returncode != 0:
            return self._err(proc.stderr.strip() or f"Package not found: {package}")
        fields: Dict[str, str] = {}
        for line in proc.stdout.splitlines():
            if ":" in line and not line.startswith(" "):
                k, v = line.split(":", 1)
                fields[k.strip()] = v.strip()
        return self._ok({"package": package, "sync": sync, "info": fields, "raw_lines": len(proc.stdout.splitlines())})

    def list_installed(self, args: Dict[str, Any]) -> ToolResult:
        if not self._pacman_available():
            return self._err("pacman not available")
        limit = max(1, min(int(args.get("limit", self.max_results)), 2000))
        query = str(args.get("query", "")).strip().lower()
        proc = self._run_pacman(["-Q"])
        if proc.returncode != 0:
            return self._err(proc.stderr.strip() or "pacman -Q failed")
        packages = []
        for line in proc.stdout.splitlines():
            parts = line.split()
            if len(parts) >= 2:
                if not query or query in parts[0].lower():
                    packages.append({"name": parts[0], "version": parts[1]})
            if len(packages) >= limit:
                break
        return self._ok({"packages": packages, "count": len(packages), "query": query or None})

    def list_files(self, args: Dict[str, Any]) -> ToolResult:
        if not self._pacman_available():
            return self._err("pacman not available")
        package = str(args.get("package", "")).strip()
        if not package:
            return self._err("package is required")
        proc = self._run_pacman(["-Ql", package])
        if proc.returncode != 0:
            return self._err(proc.stderr.strip() or f"Package not installed: {package}")
        files = [line.split(None, 1)[1] if " " in line else line for line in proc.stdout.splitlines()]
        return self._ok({"package": package, "files": files, "count": len(files)})

    def dependencies(self, args: Dict[str, Any]) -> ToolResult:
        if not self._pacman_available():
            return self._err("pacman not available")
        package = str(args.get("package", "")).strip()
        if not package:
            return self._err("package is required")
        sync = bool(args.get("sync", False))
        info = self.info({"package": package, "sync": sync})
        if not info.success:
            return info
        fields = info.content["info"]
        deps = [d.strip() for d in fields.get("Depends On", "").split() if d.strip()] if fields.get("Depends On") else []
        opt = [d.strip() for d in fields.get("Optional Deps", "").split() if d.strip()] if fields.get("Optional Deps") else []
        provides = [d.strip() for d in fields.get("Provides", "").split() if d.strip()] if fields.get("Provides") else []
        conflicts = [d.strip() for d in fields.get("Conflicts With", "").split() if d.strip()] if fields.get("Conflicts With") else []
        return self._ok({"package": package, "sync": sync, "depends_on": deps, "optional_deps": opt, "provides": provides, "conflicts_with": conflicts})

    def updates(self, args: Dict[str, Any]) -> ToolResult:
        if not self._pacman_available():
            return self._err("pacman not available")
        refresh = bool(args.get("refresh", False))
        cmd = ["-Qu"]
        if refresh:
            sync = self._run_pacman(["-Sy"], timeout=self.timeout_seconds)
            if sync.returncode != 0:
                return self._err(sync.stderr.strip() or "pacman -Sy failed")
        proc = self._run_pacman(cmd)
        if proc.returncode not in (0, 1):
            return self._err(proc.stderr.strip() or "pacman -Qu failed")
        updates = []
        for line in proc.stdout.splitlines():
            parts = line.split()
            if len(parts) >= 2:
                updates.append({"name": parts[0], "current": parts[1], "available": parts[2] if len(parts) > 2 else ""})
        return self._ok({"updates": updates, "count": len(updates), "refreshed": refresh})

    # ---- privileged operations ----
    def _authorize(self, args: Dict[str, Any]) -> Optional[str]:
        if not (args.get("approved") or args.get("_approved")):
            return "Privileged pacman operation requires approved=true"
        if not self.allow_mutating:
            return "Mutating pacman operations are disabled by server config (allow_mutating=false)"
        return None

    def install(self, args: Dict[str, Any]) -> ToolResult:
        if not self._pacman_available():
            return self._err("pacman not available")
        auth_err = self._authorize(args)
        if auth_err:
            return self._err(auth_err)
        packages = [str(p).strip() for p in (args.get("packages") or []) if str(p).strip()]
        if not packages:
            return self._err("packages is required")
        cmd = ["-S", "--noconfirm"]
        if args.get("refresh"):
            cmd.append("-y")
        cmd += packages
        proc = self._run_pacman(cmd, privileged=True)
        ok = proc.returncode == 0
        return ToolResult(success=ok, content={"command": cmd, "returncode": proc.returncode, "stdout": proc.stdout[-4000:], "stderr": proc.stderr[-2000:], "installed": packages}, error=None if ok else (proc.stderr.strip() or "pacman install failed"))

    def remove(self, args: Dict[str, Any]) -> ToolResult:
        if not self._pacman_available():
            return self._err("pacman not available")
        auth_err = self._authorize(args)
        if auth_err:
            return self._err(auth_err)
        packages = [str(p).strip() for p in (args.get("packages") or []) if str(p).strip()]
        if not packages:
            return self._err("packages is required")
        cmd = ["-R", "--noconfirm"]
        if args.get("recursive"):
            cmd[0] = "-Rs"
        if args.get("nosave"):
            cmd.append("-n")
        cmd += packages
        proc = self._run_pacman(cmd, privileged=True)
        ok = proc.returncode == 0
        return ToolResult(success=ok, content={"command": cmd, "returncode": proc.returncode, "stdout": proc.stdout[-4000:], "stderr": proc.stderr[-2000:], "removed": packages}, error=None if ok else (proc.stderr.strip() or "pacman remove failed"))

    def update(self, args: Dict[str, Any]) -> ToolResult:
        if not self._pacman_available():
            return self._err("pacman not available")
        auth_err = self._authorize(args)
        if auth_err:
            return self._err(auth_err)
        cmd = ["-S", "--noconfirm"]
        if args.get("refresh", True):
            cmd.append("-y")
        cmd.append("-u")
        proc = self._run_pacman(cmd, privileged=True, timeout=max(self.timeout_seconds, 600))
        ok = proc.returncode == 0
        return ToolResult(success=ok, content={"command": cmd, "returncode": proc.returncode, "stdout": proc.stdout[-4000:], "stderr": proc.stderr[-2000:]}, error=None if ok else (proc.stderr.strip() or "pacman update failed"))