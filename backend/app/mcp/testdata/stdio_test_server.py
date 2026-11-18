#!/usr/bin/env python3
"""Minimal stdio MCP server for transport/integration tests (JSON-RPC 2.0, line-delimited)."""
import json
import sys

PROTOCOL = "2024-11-05"


def send(msg):
    sys.stdout.write(json.dumps(msg, separators=(",", ":")) + "\n")
    sys.stdout.flush()


def handle(req):
    req_id = req.get("id")
    method = req.get("method")
    params = req.get("params") or {}
    if method == "initialize":
        return {"jsonrpc": "2.0", "id": req_id, "result": {
            "protocolVersion": PROTOCOL,
            "capabilities": {"tools": {}, "resources": {}, "prompts": {}},
            "serverInfo": {"name": "nexus-test-stdio", "version": "1.0.0"},
        }}
    if method == "notifications/initialized":
        return None
    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": req_id, "result": {"tools": [
            {"name": "echo", "description": "Echo back text", "inputSchema": {"type": "object", "properties": {"text": {"type": "string"}}, "required": ["text"]}},
            {"name": "add", "description": "Add two numbers", "inputSchema": {"type": "object", "properties": {"a": {"type": "number"}, "b": {"type": "number"}}, "required": ["a", "b"]}},
            {"name": "fail", "description": "Always fails", "inputSchema": {"type": "object", "properties": {"reason": {"type": "string"}}}},
        ]}}
    if method == "resources/list":
        return {"jsonrpc": "2.0", "id": req_id, "result": {"resources": [
            {"uri": "test://readme", "name": "readme", "description": "Test resource", "mimeType": "text/plain"}
        ]}}
    if method == "prompts/list":
        return {"jsonrpc": "2.0", "id": req_id, "result": {"prompts": [
            {"name": "greet", "description": "Greeting prompt", "arguments": [{"name": "name", "description": "Name", "required": False}]}
        ]}}
    if method == "tools/call":
        name = params.get("name")
        args = params.get("arguments") or {}
        if name == "echo":
            text = str(args.get("text", ""))
            return {"jsonrpc": "2.0", "id": req_id, "result": {"content": [{"type": "text", "text": text}]}}
        if name == "add":
            try:
                a = float(args.get("a", 0)); b = float(args.get("b", 0))
                s = a + b
                if s == int(s):
                    s = int(s)
                return {"jsonrpc": "2.0", "id": req_id, "result": {"content": [{"type": "text", "text": str(s)}], "structuredContent": {"sum": s}}}
            except Exception as e:
                return {"jsonrpc": "2.0", "id": req_id, "result": {"content": [{"type": "text", "text": str(e)}], "isError": True}}
        if name == "fail":
            reason = str(args.get("reason", "intentional failure"))
            return {"jsonrpc": "2.0", "id": req_id, "result": {"content": [{"type": "text", "text": reason}], "isError": True}}
        return {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32601, "message": f"Unknown tool: {name}"}}
    if method == "ping":
        return {"jsonrpc": "2.0", "id": req_id, "result": {}}
    # unknown -> method not found for requests with id
    if req_id is not None:
        return {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32601, "message": f"Method not found: {method}"}}
    return None


def main():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except Exception:
            continue
        if not isinstance(req, dict):
            continue
        resp = handle(req)
        if resp is not None:
            send(resp)


if __name__ == "__main__":
    main()
