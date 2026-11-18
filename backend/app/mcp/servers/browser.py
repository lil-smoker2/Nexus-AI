"""Browser MCP server: web fetch/navigation primitives and session placeholders."""

from __future__ import annotations

import re
import uuid
from typing import Any, Dict
from urllib.parse import urljoin

from app.mcp.base import BaseMcpServer, McpServerConfig, ToolDefinition, ToolResult


class BrowserMcpServer(BaseMcpServer):
    server_type = "browser"

    def __init__(self, config: McpServerConfig):
        super().__init__(config)
        self._sessions: Dict[str, Dict[str, Any]] = {}
        self._register_tools()

    def _register_tools(self) -> None:
        t = self.register_tool
        t(ToolDefinition("browser.create_session", "Create a browser session (fetch-based)", {"type":"object","properties":{}}, "read"), self.create_session)
        t(ToolDefinition("browser.close_session", "Close a browser session", {"type":"object","properties":{"session_id":{"type":"string"}},"required":["session_id"]}, "read"), self.close_session)
        t(ToolDefinition("browser.navigate", "Fetch a URL and return page info", {"type":"object","properties":{"url":{"type":"string"},"session_id":{"type":"string"}},"required":["url"]}, "read"), self.navigate)
        t(ToolDefinition("browser.get_page_info", "Fetch page title/text snippet", {"type":"object","properties":{"url":{"type":"string"}},"required":["url"]}, "read"), self.navigate)
        t(ToolDefinition("browser.inspect_page", "Inspect page content and metadata", {"type":"object","properties":{"url":{"type":"string"}},"required":["url"]}, "read"), self.navigate)
        t(ToolDefinition("browser.extract_links", "Extract links from a page", {"type":"object","properties":{"url":{"type":"string"},"limit":{"type":"integer"}},"required":["url"]}, "read"), self.extract_links)
        t(ToolDefinition("browser.capture_page", "Capture page text snapshot", {"type":"object","properties":{"url":{"type":"string"}},"required":["url"]}, "read"), self.navigate)
        t(ToolDefinition("browser.list_sessions", "List active browser sessions", {"type":"object","properties":{}}, "read"), self.list_sessions)

    def _fetch(self, url: str):
        try:
            import httpx
        except Exception as e:
            raise RuntimeError("httpx is required for browser MCP (pip install httpx)") from e
        if not re.match(r"^https?://", url):
            url = "https://" + url
        headers = {"User-Agent": "NEXUS-AI-MCP/1.0"}
        timeout = float(((self.config.config or {}).get("timeout_ms") or 15000) / 1000.0)
        with httpx.Client(follow_redirects=True, timeout=timeout, headers=headers) as client:
            return client.get(url)

    def create_session(self, args: Dict[str, Any]) -> ToolResult:
        sid = str(uuid.uuid4())
        self._sessions[sid] = {"id": sid, "current_url": None, "engine": "http-fetch"}
        return ToolResult(success=True, content=self._sessions[sid])

    def close_session(self, args: Dict[str, Any]) -> ToolResult:
        sid = str(args.get("session_id") or "")
        if sid in self._sessions:
            del self._sessions[sid]
            return ToolResult(success=True, content={"session_id": sid, "closed": True})
        return ToolResult(success=False, error="Session not found")

    def list_sessions(self, args: Dict[str, Any]) -> ToolResult:
        return ToolResult(success=True, content={"sessions": list(self._sessions.values()), "count": len(self._sessions)})

    def navigate(self, args: Dict[str, Any]) -> ToolResult:
        url = str(args.get("url", "")).strip()
        if not url:
            return ToolResult(success=False, error="url is required")
        try:
            r = self._fetch(url)
            text = r.text or ""
            title = ""
            m = re.search(r"<title[^>]*>(.*?)</title>", text, re.I | re.S)
            if m:
                title = re.sub(r"\s+", " ", m.group(1)).strip()
            snippet = re.sub(r"<script[\s\S]*?</script>|<style[\s\S]*?</style>", " ", text, flags=re.I)
            snippet = re.sub(r"<[^>]+>", " ", snippet)
            snippet = re.sub(r"\s+", " ", snippet).strip()[:4000]
            sid = args.get("session_id")
            if sid and sid in self._sessions:
                self._sessions[sid]["current_url"] = str(r.url)
                self._sessions[sid]["last_status"] = r.status_code
            return ToolResult(success=True, content={
                "url": str(r.url), "status_code": r.status_code, "title": title,
                "content_type": r.headers.get("content-type"), "text_snippet": snippet,
                "session_id": sid if sid in self._sessions else None,
            })
        except Exception as e:
            return ToolResult(success=False, error=str(e))

    def extract_links(self, args: Dict[str, Any]) -> ToolResult:
        url = str(args.get("url", "")).strip()
        limit = min(int(args.get("limit", 50)), 500)
        if not url:
            return ToolResult(success=False, error="url is required")
        try:
            r = self._fetch(url)
            hrefs = re.findall(r'href=["\']([^"\']+)["\']', r.text or "", re.I)
            links = []
            seen = set()
            for h in hrefs:
                absu = urljoin(str(r.url), h)
                if absu in seen:
                    continue
                seen.add(absu)
                links.append(absu)
                if len(links) >= limit:
                    break
            return ToolResult(success=True, content={"url": str(r.url), "links": links, "count": len(links)})
        except Exception as e:
            return ToolResult(success=False, error=str(e))
