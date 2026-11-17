"""Browser MCP server: basic web fetch/navigation primitives (httpx-based)."""

from __future__ import annotations

import re
from typing import Any, Dict
from urllib.parse import urljoin

from app.mcp.base import BaseMcpServer, McpServerConfig, ToolDefinition, ToolResult


class BrowserMcpServer(BaseMcpServer):
    server_type = "browser"

    def __init__(self, config: McpServerConfig):
        super().__init__(config)
        self._register_tools()

    def _register_tools(self) -> None:
        t = self.register_tool
        t(ToolDefinition("browser.navigate", "Fetch a URL and return page info", {"type":"object","properties":{"url":{"type":"string"}},"required":["url"]}, "read"), self.navigate)
        t(ToolDefinition("browser.get_page_info", "Fetch page title/text snippet", {"type":"object","properties":{"url":{"type":"string"}},"required":["url"]}, "read"), self.navigate)
        t(ToolDefinition("browser.extract_links", "Extract links from a page", {"type":"object","properties":{"url":{"type":"string"},"limit":{"type":"integer"}},"required":["url"]}, "read"), self.extract_links)

    def _fetch(self, url: str):
        try:
            import httpx
        except Exception as e:
            raise RuntimeError("httpx is required for browser MCP (pip install httpx)") from e
        if not re.match(r"^https?://", url):
            url = "https://" + url
        headers = {"User-Agent": "NEXUS-AI-MCP/1.0"}
        with httpx.Client(follow_redirects=True, timeout=15.0, headers=headers) as client:
            return client.get(url)

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
            snippet = re.sub(r"\s+", " ", snippet).strip()[:2000]
            return ToolResult(success=True, content={
                "url": str(r.url), "status_code": r.status_code, "title": title,
                "content_type": r.headers.get("content-type"), "text_snippet": snippet,
            })
        except Exception as e:
            return ToolResult(success=False, error=str(e))

    def extract_links(self, args: Dict[str, Any]) -> ToolResult:
        url = str(args.get("url", "")).strip()
        limit = int(args.get("limit", 50))
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
