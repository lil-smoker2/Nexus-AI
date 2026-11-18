"""Stdio MCP client: spawns a local process and speaks JSON-RPC over stdio."""

from __future__ import annotations

import json
import os
import queue
import subprocess
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from app.mcp.protocol import (
    DEFAULT_PROTOCOL_VERSION,
    McpCapabilities,
    NormalizedToolResult,
    decode_message,
    encode_message,
    new_id,
    notification,
    request,
)


class StdioMcpError(Exception):
    pass


class StdioMcpClient:
    """Synchronous stdio MCP client with background reader thread."""

    def __init__(
        self,
        command: str,
        args: Optional[List[str]] = None,
        env: Optional[Dict[str, str]] = None,
        cwd: Optional[str] = None,
        timeout_ms: int = 30000,
        client_name: str = "nexus-ai",
        client_version: str = "0.1.0",
    ):
        self.command = command
        self.args = args or []
        self.env = {**os.environ, **(env or {})}
        self.cwd = cwd
        self.timeout_ms = timeout_ms
        self.client_name = client_name
        self.client_version = client_version

        self.proc: Optional[subprocess.Popen] = None
        self._reader: Optional[threading.Thread] = None
        self._stderr_reader: Optional[threading.Thread] = None
        self._responses: "queue.Queue[Dict[str, Any]]" = queue.Queue()
        self._notifications: "queue.Queue[Dict[str, Any]]" = queue.Queue()
        self._pending: Dict[Any, "queue.Queue[Dict[str, Any]]"] = {}
        self._pending_lock = threading.Lock()
        self._stderr_lines: List[str] = []
        self._stderr_lock = threading.Lock()
        self._closed = False

        self.connected = False
        self.initialize_result: Dict[str, Any] = {}
        self.capabilities = McpCapabilities()
        self.server_info: Dict[str, Any] = {}
        self.protocol_version: Optional[str] = None

    def start(self) -> None:
        if self.proc and self.proc.poll() is None:
            return
        self._closed = False
        cmd = [self.command] + list(self.args)
        self.proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=self.cwd,
            env=self.env,
            bufsize=0,
        )
        self._reader = threading.Thread(target=self._read_stdout, daemon=True)
        self._reader.start()
        self._stderr_reader = threading.Thread(target=self._read_stderr, daemon=True)
        self._stderr_reader.start()

    def _read_stdout(self) -> None:
        try:
            assert self.proc and self.proc.stdout
            for raw in iter(self.proc.stdout.readline, b""):
                if not raw:
                    break
                try:
                    line = raw.decode("utf-8", errors="replace")
                except Exception:
                    continue
                msg = decode_message(line)
                if not msg:
                    continue
                if "id" in msg and ("result" in msg or "error" in msg):
                    req_id = msg.get("id")
                    with self._pending_lock:
                        q = self._pending.get(req_id)
                    if q:
                        q.put(msg)
                    else:
                        self._responses.put(msg)
                elif "method" in msg:
                    self._notifications.put(msg)
        except Exception:
            pass
        finally:
            # unblock waiters
            with self._pending_lock:
                for q in self._pending.values():
                    q.put({"jsonrpc": "2.0", "id": None, "error": {"code": -32000, "message": "Connection closed"}})
                self._pending.clear()

    def _read_stderr(self) -> None:
        try:
            assert self.proc and self.proc.stderr
            for raw in iter(self.proc.stderr.readline, b""):
                if not raw:
                    break
                line = raw.decode("utf-8", errors="replace").rstrip()
                with self._stderr_lock:
                    self._stderr_lines.append(line)
                    if len(self._stderr_lines) > 200:
                        self._stderr_lines = self._stderr_lines[-200:]
        except Exception:
            pass

    def _send(self, msg: Dict[str, Any]) -> None:
        if not self.proc or self.proc.stdin is None:
            raise StdioMcpError("Process not started")
        if self.proc.poll() is not None:
            raise StdioMcpError("Process exited")
        data = encode_message(msg)
        try:
            self.proc.stdin.write(data)
            self.proc.stdin.flush()
        except Exception as e:
            raise StdioMcpError(f"Failed to write to process: {e}") from e

    def request(self, method: str, params: Optional[Dict[str, Any]] = None, timeout_ms: Optional[int] = None) -> Dict[str, Any]:
        req_id = new_id()
        msg = request(method, params=params, req_id=req_id)
        q: "queue.Queue[Dict[str, Any]]" = queue.Queue(maxsize=1)
        with self._pending_lock:
            self._pending[req_id] = q
        try:
            self._send(msg)
            timeout = (timeout_ms if timeout_ms is not None else self.timeout_ms) / 1000.0
            try:
                resp = q.get(timeout=timeout)
            except queue.Empty:
                raise StdioMcpError(f"Timeout waiting for response to {method}")
            if "error" in resp and resp.get("error"):
                err = resp.get("error") or {}
                raise StdioMcpError(err.get("message") or str(err))
            return resp.get("result") or {}
        finally:
            with self._pending_lock:
                self._pending.pop(req_id, None)

    def notify(self, method: str, params: Optional[Dict[str, Any]] = None) -> None:
        self._send(notification(method, params=params))

    def initialize(self) -> Dict[str, Any]:
        self.start()
        params = {
            "protocolVersion": DEFAULT_PROTOCOL_VERSION,
            "capabilities": {},
            "clientInfo": {"name": self.client_name, "version": self.client_version},
        }
        result = self.request("initialize", params=params)
        self.initialize_result = result or {}
        self.capabilities = McpCapabilities.from_result(self.initialize_result)
        self.server_info = (self.initialize_result or {}).get("serverInfo") or {}
        self.protocol_version = (self.initialize_result or {}).get("protocolVersion")
        try:
            self.notify("notifications/initialized", {})
        except Exception:
            pass
        self.connected = True
        return self.initialize_result

    def list_tools(self) -> List[Dict[str, Any]]:
        if not self.capabilities.tools and self.initialize_result:
            # some servers omit explicit capability but support tools/list
            pass
        result = self.request("tools/list", params={})
        tools = (result or {}).get("tools") or []
        return tools if isinstance(tools, list) else []

    def list_resources(self) -> List[Dict[str, Any]]:
        try:
            result = self.request("resources/list", params={})
            resources = (result or {}).get("resources") or []
            return resources if isinstance(resources, list) else []
        except Exception:
            return []

    def list_prompts(self) -> List[Dict[str, Any]]:
        try:
            result = self.request("prompts/list", params={})
            prompts = (result or {}).get("prompts") or []
            return prompts if isinstance(prompts, list) else []
        except Exception:
            return []

    def call_tool(self, name: str, arguments: Optional[Dict[str, Any]] = None, timeout_ms: Optional[int] = None) -> NormalizedToolResult:
        result = self.request("tools/call", params={"name": name, "arguments": arguments or {}}, timeout_ms=timeout_ms)
        return NormalizedToolResult.from_mcp(result if isinstance(result, dict) else {"content": result})

    def health(self) -> Dict[str, Any]:
        alive = self.proc is not None and self.proc.poll() is None
        with self._stderr_lock:
            stderr_tail = list(self._stderr_lines[-10:])
        return {"connected": self.connected and alive, "process_alive": alive, "stderr_tail": stderr_tail}

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        self.connected = False
        proc = self.proc
        self.proc = None
        if proc:
            try:
                if proc.stdin:
                    proc.stdin.close()
            except Exception:
                pass
            try:
                proc.terminate()
                proc.wait(timeout=2)
            except Exception:
                try:
                    proc.kill()
                except Exception:
                    pass
