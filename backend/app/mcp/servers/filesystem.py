"""Filesystem MCP server: file and directory operations within allowed roots."""

from __future__ import annotations

import fnmatch
import os
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.mcp.base import BaseMcpServer, McpServerConfig, ToolDefinition, ToolResult


DEFAULT_DENY_PATTERNS = [".env", "*.pem", "*.key", "id_rsa", "id_ed25519", ".ssh/*"]
MAX_READ_BYTES = 1024 * 1024  # 1MB
MAX_ENTRIES = 5000
MAX_SEARCH_RESULTS = 1000


def _is_denied(rel: str, patterns: List[str]) -> bool:
    rel_norm = rel.replace("\\", "/")
    name = os.path.basename(rel_norm)
    for pat in patterns:
        if fnmatch.fnmatch(rel_norm, pat) or fnmatch.fnmatch(name, pat):
            return True
    return False


class FilesystemMcpServer(BaseMcpServer):
    server_type = "filesystem"

    def __init__(self, config: McpServerConfig):
        super().__init__(config)
        cfg = config.config or {}
        root = (config.args[0] if config.args else None) or cfg.get("root") or config.env.get("ROOT") or os.getcwd()
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.deny_patterns = list(cfg.get("deny_patterns") or DEFAULT_DENY_PATTERNS)
        self.max_read_bytes = int(cfg.get("max_read_bytes") or MAX_READ_BYTES)
        self.max_entries = int(cfg.get("max_entries") or MAX_ENTRIES)
        self.max_search_results = int(cfg.get("max_search_results") or MAX_SEARCH_RESULTS)
        self._register_tools()

    def _ok(self, content: Any = None, **meta: Any) -> ToolResult:
        return ToolResult(success=True, content=content, metadata=meta)

    def _err(self, msg: str) -> ToolResult:
        return ToolResult(success=False, error=msg)

    def _resolve(self, path: str) -> Path:
        p = (self.root / path).resolve() if not os.path.isabs(path) else Path(path).resolve()
        try:
            p.relative_to(self.root)
        except Exception:
            if p != self.root:
                raise ValueError(f"Path escapes allowed root: {path}")
        return p

    def _rel(self, p: Path) -> str:
        try:
            return str(p.relative_to(self.root))
        except Exception:
            return str(p)

    def _check_denied(self, p: Path) -> Optional[str]:
        rel = self._rel(p)
        if _is_denied(rel, self.deny_patterns):
            return f"Access denied for sensitive path: {rel}"
        return None

    def _register_tools(self) -> None:
        t = self.register_tool
        t(ToolDefinition("fs.create_file", "Create a file", {"type":"object","properties":{"path":{"type":"string"},"content":{"type":"string"},"overwrite":{"type":"boolean"}},"required":["path"]}, "write"), self.create_file)
        t(ToolDefinition("fs.create_directory", "Create a directory", {"type":"object","properties":{"path":{"type":"string"},"recursive":{"type":"boolean"}},"required":["path"]}, "write"), self.create_directory)
        t(ToolDefinition("fs.read_file", "Read a file", {"type":"object","properties":{"path":{"type":"string"},"encoding":{"type":"string"},"offset":{"type":"integer"},"limit":{"type":"integer"}},"required":["path"]}, "read"), self.read_file)
        t(ToolDefinition("fs.write_file", "Write/replace a file", {"type":"object","properties":{"path":{"type":"string"},"content":{"type":"string"},"create_if_missing":{"type":"boolean"}},"required":["path","content"]}, "write"), self.write_file)
        t(ToolDefinition("fs.append_file", "Append to a file", {"type":"object","properties":{"path":{"type":"string"},"content":{"type":"string"}},"required":["path","content"]}, "write"), self.append_file)
        t(ToolDefinition("fs.edit_file", "Replace text in a file", {"type":"object","properties":{"path":{"type":"string"},"old":{"type":"string"},"new":{"type":"string"},"replace_all":{"type":"boolean"}},"required":["path","old","new"]}, "write"), self.edit_file)
        t(ToolDefinition("fs.delete_file", "Delete a file", {"type":"object","properties":{"path":{"type":"string"}},"required":["path"]}, "destructive"), self.delete_file)
        t(ToolDefinition("fs.delete_directory", "Delete a directory", {"type":"object","properties":{"path":{"type":"string"},"recursive":{"type":"boolean"}},"required":["path"]}, "destructive"), self.delete_directory)
        t(ToolDefinition("fs.copy_file", "Copy a file", {"type":"object","properties":{"source":{"type":"string"},"destination":{"type":"string"},"overwrite":{"type":"boolean"}},"required":["source","destination"]}, "write"), self.copy_file)
        t(ToolDefinition("fs.copy_directory", "Copy a directory", {"type":"object","properties":{"source":{"type":"string"},"destination":{"type":"string"}},"required":["source","destination"]}, "write"), self.copy_directory)
        t(ToolDefinition("fs.move_path", "Move/rename a path", {"type":"object","properties":{"source":{"type":"string"},"destination":{"type":"string"},"overwrite":{"type":"boolean"}},"required":["source","destination"]}, "destructive"), self.move_path)
        t(ToolDefinition("fs.list_directory", "List directory entries", {"type":"object","properties":{"path":{"type":"string"},"recursive":{"type":"boolean"},"include_hidden":{"type":"boolean"}},"required":[]}, "read"), self.list_directory)
        t(ToolDefinition("fs.search_files", "Search files by glob/name", {"type":"object","properties":{"path":{"type":"string"},"pattern":{"type":"string"},"max_results":{"type":"integer"}},"required":["pattern"]}, "read"), self.search_files)
        t(ToolDefinition("fs.search_content", "Search text content in files", {"type":"object","properties":{"path":{"type":"string"},"query":{"type":"string"},"glob":{"type":"string"},"max_results":{"type":"integer"}},"required":["query"]}, "read"), self.search_content)
        t(ToolDefinition("fs.stat", "Get path metadata", {"type":"object","properties":{"path":{"type":"string"}},"required":["path"]}, "read"), self.stat_path)
        t(ToolDefinition("fs.get_metadata", "Get path metadata (alias)", {"type":"object","properties":{"path":{"type":"string"}},"required":["path"]}, "read"), self.stat_path)
        t(ToolDefinition("fs.exists", "Check path existence", {"type":"object","properties":{"path":{"type":"string"}},"required":["path"]}, "read"), self.exists)

    def _path(self, args: Dict[str, Any], key: str = "path") -> Path:
        return self._resolve(str(args.get(key, ".")))

    def create_file(self, args: Dict[str, Any]) -> ToolResult:
        try:
            p = self._path(args)
            denied = self._check_denied(p)
            if denied:
                return self._err(denied)
            overwrite = bool(args.get("overwrite", False))
            if p.exists() and not overwrite:
                return self._err(f"File exists: {p}")
            p.parent.mkdir(parents=True, exist_ok=True)
            content = args.get("content", "") or ""
            if len(content.encode("utf-8", errors="ignore")) > self.max_read_bytes:
                return self._err("Content exceeds max allowed size")
            p.write_text(content, encoding="utf-8")
            return self._ok({"path": str(p), "created": True, "exists": p.exists(), "size": p.stat().st_size})
        except Exception as e:
            return self._err(str(e))

    def create_directory(self, args: Dict[str, Any]) -> ToolResult:
        try:
            p = self._path(args)
            recursive = bool(args.get("recursive", True))
            p.mkdir(parents=recursive, exist_ok=True)
            return self._ok({"path": str(p), "is_dir": p.is_dir(), "exists": p.exists()})
        except Exception as e:
            return self._err(str(e))

    def read_file(self, args: Dict[str, Any]) -> ToolResult:
        try:
            p = self._path(args)
            denied = self._check_denied(p)
            if denied:
                return self._err(denied)
            if not p.exists() or not p.is_file():
                return self._err(f"File not found: {p}")
            if p.stat().st_size > self.max_read_bytes and not args.get("offset") and not args.get("limit"):
                with p.open("r", encoding=args.get("encoding", "utf-8"), errors="replace") as f:
                    data = f.read(self.max_read_bytes)
                return self._ok({"path": str(p), "content": data, "truncated": True, "size": p.stat().st_size})
            enc = args.get("encoding", "utf-8")
            data = p.read_text(encoding=enc, errors="replace")
            offset = int(args.get("offset") or 0)
            limit = args.get("limit")
            if offset:
                data = data[offset:]
            if limit is not None:
                data = data[: int(limit)]
            truncated = len(data.encode("utf-8", errors="ignore")) >= self.max_read_bytes
            return self._ok({"path": str(p), "content": data[: self.max_read_bytes], "truncated": truncated, "size": p.stat().st_size})
        except Exception as e:
            return self._err(str(e))

    def write_file(self, args: Dict[str, Any]) -> ToolResult:
        try:
            p = self._path(args)
            denied = self._check_denied(p)
            if denied:
                return self._err(denied)
            create = bool(args.get("create_if_missing", True))
            if not p.exists() and not create:
                return self._err(f"File not found: {p}")
            p.parent.mkdir(parents=True, exist_ok=True)
            content = args.get("content", "")
            p.write_text(content, encoding="utf-8")
            return self._ok({"path": str(p), "written": True, "exists": p.exists(), "size": p.stat().st_size})
        except Exception as e:
            return self._err(str(e))

    def append_file(self, args: Dict[str, Any]) -> ToolResult:
        try:
            p = self._path(args)
            denied = self._check_denied(p)
            if denied:
                return self._err(denied)
            p.parent.mkdir(parents=True, exist_ok=True)
            with p.open("a", encoding="utf-8") as f:
                f.write(args.get("content", ""))
            return self._ok({"path": str(p), "appended": True, "exists": p.exists(), "size": p.stat().st_size})
        except Exception as e:
            return self._err(str(e))

    def edit_file(self, args: Dict[str, Any]) -> ToolResult:
        try:
            p = self._path(args)
            denied = self._check_denied(p)
            if denied:
                return self._err(denied)
            if not p.exists() or not p.is_file():
                return self._err(f"File not found: {p}")
            old = str(args.get("old", ""))
            new = str(args.get("new", ""))
            replace_all = bool(args.get("replace_all", False))
            text = p.read_text(encoding="utf-8")
            if old not in text:
                return self._err("old string not found")
            count = text.count(old)
            if count > 1 and not replace_all:
                return self._err("multiple matches; set replace_all or provide unique old string")
            text = text.replace(old, new) if replace_all else text.replace(old, new, 1)
            p.write_text(text, encoding="utf-8")
            return self._ok({"path": str(p), "replaced": count if replace_all else 1, "exists": p.exists()})
        except Exception as e:
            return self._err(str(e))

    def delete_file(self, args: Dict[str, Any]) -> ToolResult:
        try:
            p = self._path(args)
            denied = self._check_denied(p)
            if denied:
                return self._err(denied)
            if not p.exists():
                return self._err(f"Not found: {p}")
            if p.is_dir():
                return self._err("Path is a directory; use fs.delete_directory")
            p.unlink()
            return self._ok({"path": str(p), "deleted": True, "exists": p.exists()})
        except Exception as e:
            return self._err(str(e))

    def delete_directory(self, args: Dict[str, Any]) -> ToolResult:
        try:
            p = self._path(args)
            recursive = bool(args.get("recursive", False))
            if not p.exists():
                return self._err(f"Not found: {p}")
            if not p.is_dir():
                return self._err("Path is not a directory")
            if recursive:
                shutil.rmtree(p)
            else:
                p.rmdir()
            return self._ok({"path": str(p), "deleted": True, "exists": p.exists()})
        except Exception as e:
            return self._err(str(e))

    def copy_file(self, args: Dict[str, Any]) -> ToolResult:
        try:
            src = self._path(args, "source")
            dst = self._path(args, "destination")
            overwrite = bool(args.get("overwrite", True))
            d1 = self._check_denied(src); d2 = self._check_denied(dst)
            if d1: return self._err(d1)
            if d2: return self._err(d2)
            if not src.exists() or not src.is_file():
                return self._err(f"Source file not found: {src}")
            if dst.exists() and not overwrite:
                return self._err(f"Destination exists: {dst}")
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            return self._ok({"source": str(src), "destination": str(dst), "copied": True, "source_exists": src.exists(), "destination_exists": dst.exists(), "size": dst.stat().st_size if dst.exists() else None})
        except Exception as e:
            return self._err(str(e))

    def copy_directory(self, args: Dict[str, Any]) -> ToolResult:
        try:
            src = self._path(args, "source")
            dst = self._path(args, "destination")
            if not src.exists() or not src.is_dir():
                return self._err(f"Source directory not found: {src}")
            if dst.exists():
                shutil.rmtree(dst)
            shutil.copytree(src, dst)
            return self._ok({"source": str(src), "destination": str(dst), "copied": True, "destination_exists": dst.exists()})
        except Exception as e:
            return self._err(str(e))

    def move_path(self, args: Dict[str, Any]) -> ToolResult:
        try:
            src = self._path(args, "source")
            dst = self._path(args, "destination")
            overwrite = bool(args.get("overwrite", True))
            if not src.exists():
                return self._err(f"Source not found: {src}")
            if dst.exists():
                if not overwrite:
                    return self._err(f"Destination exists: {dst}")
                if dst.is_dir():
                    shutil.rmtree(dst)
                else:
                    dst.unlink()
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), str(dst))
            return self._ok({"source": str(src), "destination": str(dst), "moved": True, "source_exists": src.exists(), "destination_exists": dst.exists()})
        except Exception as e:
            return self._err(str(e))

    def list_directory(self, args: Dict[str, Any]) -> ToolResult:
        try:
            p = self._path(args)
            recursive = bool(args.get("recursive", False))
            include_hidden = bool(args.get("include_hidden", True))
            if not p.exists() or not p.is_dir():
                return self._err(f"Directory not found: {p}")
            entries: List[Dict[str, Any]] = []
            it = p.rglob("*") if recursive else p.iterdir()
            for child in sorted(it, key=lambda x: str(x)):
                if not include_hidden and child.name.startswith("."):
                    continue
                entries.append(self._entry(child))
                if len(entries) >= self.max_entries:
                    break
            return self._ok({"path": str(p), "entries": entries, "count": len(entries), "truncated": len(entries) >= self.max_entries})
        except Exception as e:
            return self._err(str(e))

    def _entry(self, p: Path) -> Dict[str, Any]:
        try:
            st = p.stat()
            return {"name": p.name, "path": str(p), "type": "directory" if p.is_dir() else "file", "size": st.st_size, "mtime": st.st_mtime}
        except Exception:
            return {"name": p.name, "path": str(p), "type": "directory" if p.is_dir() else "file"}

    def search_files(self, args: Dict[str, Any]) -> ToolResult:
        try:
            base = self._path(args)
            pattern = str(args.get("pattern", "*"))
            max_results = min(int(args.get("max_results", 200)), self.max_search_results)
            if not base.exists():
                return self._err(f"Path not found: {base}")
            matches: List[str] = []
            it = base.rglob("*") if base.is_dir() else [base]
            for child in it:
                name = child.name
                try:
                    rel = str(child.relative_to(self.root))
                except Exception:
                    rel = str(child)
                if fnmatch.fnmatch(name, pattern) or fnmatch.fnmatch(rel, pattern):
                    matches.append(str(child))
                if len(matches) >= max_results:
                    break
            return self._ok({"pattern": pattern, "matches": matches, "count": len(matches), "truncated": len(matches) >= max_results})
        except Exception as e:
            return self._err(str(e))

    def search_content(self, args: Dict[str, Any]) -> ToolResult:
        try:
            base = self._path(args)
            query = str(args.get("query", ""))
            glob_pat = str(args.get("glob") or "*")
            max_results = min(int(args.get("max_results", 100)), self.max_search_results)
            if not query:
                return self._err("query is required")
            if not base.exists():
                return self._err(f"Path not found: {base}")
            results = []
            files = base.rglob("*") if base.is_dir() else [base]
            for p in files:
                if len(results) >= max_results:
                    break
                if not p.is_file():
                    continue
                if not fnmatch.fnmatch(p.name, glob_pat) and not fnmatch.fnmatch(str(p), glob_pat):
                    continue
                denied = self._check_denied(p)
                if denied:
                    continue
                try:
                    if p.stat().st_size > self.max_read_bytes:
                        continue
                    text = p.read_text(encoding="utf-8", errors="ignore")
                except Exception:
                    continue
                if query in text:
                    # include first matching line snippet
                    for i, line in enumerate(text.splitlines(), 1):
                        if query in line:
                            results.append({"path": str(p), "line": i, "snippet": line[:300]})
                            break
            return self._ok({"query": query, "results": results, "count": len(results), "truncated": len(results) >= max_results})
        except Exception as e:
            return self._err(str(e))

    def stat_path(self, args: Dict[str, Any]) -> ToolResult:
        try:
            p = self._path(args)
            if not p.exists():
                return self._ok({"path": str(p), "exists": False})
            st = p.stat()
            return self._ok({"path": str(p), "exists": True, "type": "directory" if p.is_dir() else "file", "size": st.st_size, "mtime": st.st_mtime, "mode": st.st_mode})
        except Exception as e:
            return self._err(str(e))

    def exists(self, args: Dict[str, Any]) -> ToolResult:
        try:
            p = self._path(args)
            return self._ok({"path": str(p), "exists": p.exists(), "is_file": p.is_file(), "is_dir": p.is_dir()})
        except Exception as e:
            return self._err(str(e))
