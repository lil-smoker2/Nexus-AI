"""Phase 6 MCP tests: transports, registry, security, audit, discovery/invocation."""

import json
import os
import shutil
import sys
import uuid
from pathlib import Path

import pytest

from app.database.session import init_db, SessionLocal
from app.database.repositories.container import Repositories
from app.mcp.manager import mcp_manager, _default_root
from app.mcp.transports.stdio import StdioMcpClient
from app.mcp.protocol import NormalizedToolResult


REPO_ROOT = Path(_default_root())


def _stdio_server():
    return [sys.executable, str(REPO_ROOT / "backend/app/mcp/testdata/stdio_test_server.py")]


def setup_module(module=None):
    init_db()
    mcp_manager.initialize()


def teardown_module(module=None):
    try:
        mcp_manager.shutdown()
    except Exception:
        pass


def _unique(name: str) -> str:
    return f"{name}-{uuid.uuid4().hex[:8]}"


def test_stdio_transport_handshake_discovery_and_calls():
    cmd = _stdio_server()
    client = StdioMcpClient(command=cmd[0], args=cmd[1:], timeout_ms=10000)
    try:
        init = client.initialize()
        assert init.get("serverInfo", {}).get("name") == "nexus-test-stdio"
        assert client.capabilities.tools is True
        tools = client.list_tools()
        names = {t["name"] for t in tools}
        assert {"echo", "add", "fail"}.issubset(names)
        resources = client.list_resources()
        assert resources and resources[0]["uri"] == "test://readme"
        prompts = client.list_prompts()
        assert prompts and prompts[0]["name"] == "greet"

        ok = client.call_tool("echo", {"text": "hello"})
        assert ok.success is True
        assert ok.content == "hello"

        add = client.call_tool("add", {"a": 2, "b": 3})
        assert add.success is True
        assert add.content in ("5", 5) or (isinstance(add.raw, dict) and add.raw.get("structuredContent", {}).get("sum") == 5)

        fail = client.call_tool("fail", {"reason": "boom"})
        assert fail.success is False
        assert "boom" in (fail.error or "")

        # reconnect behavior: close and re-init
        client.close()
        client2 = StdioMcpClient(command=cmd[0], args=cmd[1:], timeout_ms=10000)
        try:
            client2.initialize()
            again = client2.call_tool("echo", {"text": "again"})
            assert again.success and again.content == "again"
        finally:
            client2.close()
    finally:
        client.close()


def test_external_stdio_server_registration_discovery_invocation_and_audit():
    name = _unique("ext-stdio")
    cmd = _stdio_server()
    server = mcp_manager.register_server({
        "name": name,
        "description": "Test stdio MCP server",
        "transport": "stdio",
        "endpoint": cmd[0],
        "args": cmd[1:],
        "config": {"timeout_ms": 10000},
        "permissions": {"allow": ["read", "write"]},
    })
    sid = server["id"]
    try:
        # initially disconnected (external not auto-connected)
        s0 = mcp_manager.get_server(sid)
        assert s0 and s0["status"] in ("disconnected", "connected")

        conn = mcp_manager.connect(sid)
        assert conn["status"] == "connected"
        tools = conn.get("tools") or mcp_manager.list_tools(sid)
        names = {t["name"] for t in tools}
        assert "echo" in names and "add" in names

        # discovery surfaces resources/prompts
        s = mcp_manager.get_server(sid)
        assert s is not None
        assert isinstance(s.get("resources"), list)
        assert isinstance(s.get("prompts"), list)

        res = mcp_manager.call_tool(sid, "echo", {"text": "ping"})
        assert res["success"] is True
        assert res["content"] == "ping"

        bad = mcp_manager.call_tool(sid, "fail", {"reason": "nope"})
        assert bad["success"] is False

        # audit logged
        events = mcp_manager.audit_log(limit=50, server_id=sid)
        assert any(e.get("tool_name") == "echo" for e in events)
        assert any(e.get("action") == "connect" for e in events)

        # disconnect/reconnect
        mcp_manager.disconnect(sid)
        assert mcp_manager.get_server(sid)["status"] == "disconnected"
        mcp_manager.connect(sid)
        res2 = mcp_manager.call_tool(sid, "echo", {"text": "pong"})
        assert res2["success"] and res2["content"] == "pong"
    finally:
        try:
            mcp_manager.delete_server(sid)
        except Exception:
            pass


def test_registry_crud_and_health():
    name = _unique("reg")
    cmd = _stdio_server()
    s = mcp_manager.register_server({
        "name": name, "transport": "stdio", "endpoint": cmd[0], "args": cmd[1:], "config": {"timeout_ms": 10000}
    })
    sid = s["id"]
    try:
        got = mcp_manager.get_server(sid)
        assert got and got["name"] == name
        upd = mcp_manager.update_server(sid, {"description": "updated"})
        assert upd.get("description") == "updated"
        h = mcp_manager.health(sid)
        assert h["server_id"] == sid
        conn = mcp_manager.connect(sid)
        assert conn["status"] == "connected"
        h2 = mcp_manager.health(sid)
        assert h2["connected"] is True
        restarted = mcp_manager.restart(sid)
        assert restarted["status"] == "connected"
    finally:
        mcp_manager.delete_server(sid)


def test_permission_and_validation_enforcement():
    name = _unique("perm")
    cmd = _stdio_server()
    # only allow read; 'add' will be inferred as write -> should be denied
    s = mcp_manager.register_server({
        "name": name, "transport": "stdio", "endpoint": cmd[0], "args": cmd[1:],
        "config": {"timeout_ms": 10000}, "permissions": {"allow": ["read"]},
    })
    sid = s["id"]
    try:
        mcp_manager.connect(sid)
        # echo inferred read should be allowed
        ok = mcp_manager.call_tool(sid, "echo", {"text": "hi"})
        assert ok["success"] is True
        # add inferred write should be denied
        with pytest.raises(Exception):
            mcp_manager.call_tool(sid, "add", {"a": 1, "b": 2})
        # validation: missing required arg
        with pytest.raises(Exception):
            mcp_manager.call_tool(sid, "echo", {})
    finally:
        mcp_manager.delete_server(sid)


def test_tool_allowlist_and_denied_tools():
    name = _unique("allow")
    cmd = _stdio_server()
    s = mcp_manager.register_server({
        "name": name, "transport": "stdio", "endpoint": cmd[0], "args": cmd[1:],
        "config": {"timeout_ms": 10000}, "permissions": {"allow": ["read", "write"], "allowed_tools": ["echo"]},
    })
    sid = s["id"]
    try:
        mcp_manager.connect(sid)
        assert mcp_manager.call_tool(sid, "echo", {"text": "ok"})["success"] is True
        with pytest.raises(Exception):
            mcp_manager.call_tool(sid, "add", {"a": 1, "b": 2})
    finally:
        mcp_manager.delete_server(sid)


def test_filesystem_parity_and_safety():
    servers = {s["name"]: s for s in mcp_manager.list_servers()}
    fs = servers["filesystem"]["id"]
    base = "tmp_mcp_p6"
    abs_base = REPO_ROOT / base
    if abs_base.exists():
        shutil.rmtree(abs_base)
    try:
        # create/write/append/edit/read/stat/exists/search
        assert mcp_manager.call_tool(fs, "fs.create_directory", {"path": base})["success"]
        assert mcp_manager.call_tool(fs, "fs.create_file", {"path": f"{base}/a.txt", "content": "hello world", "overwrite": True})["success"]
        assert mcp_manager.call_tool(fs, "fs.append_file", {"path": f"{base}/a.txt", "content": "\nline2"})["success"]
        r_edit = mcp_manager.call_tool(fs, "fs.edit_file", {"path": f"{base}/a.txt", "old": "world", "new": "nexus", "replace_all": False})
        assert r_edit["success"]
        r_read = mcp_manager.call_tool(fs, "fs.read_file", {"path": f"{base}/a.txt"})
        assert r_read["success"] and "nexus" in r_read["content"]["content"]
        r_stat = mcp_manager.call_tool(fs, "fs.stat", {"path": f"{base}/a.txt"})
        assert r_stat["success"] and r_stat["content"]["exists"] is True
        r_exists = mcp_manager.call_tool(fs, "fs.exists", {"path": f"{base}/a.txt"})
        assert r_exists["success"] and r_exists["content"]["is_file"] is True
        r_search = mcp_manager.call_tool(fs, "fs.search_files", {"path": base, "pattern": "*.txt"})
        assert r_search["success"] and any("a.txt" in m for m in r_search["content"]["matches"])
        r_scontent = mcp_manager.call_tool(fs, "fs.search_content", {"path": base, "query": "nexus", "glob": "*.txt"})
        assert r_scontent["success"] and r_scontent["content"]["count"] >= 1
        # copy/move/delete
        assert mcp_manager.call_tool(fs, "fs.copy_file", {"source": f"{base}/a.txt", "destination": f"{base}/b.txt", "overwrite": True})["success"]
        assert mcp_manager.call_tool(fs, "fs.move_path", {"source": f"{base}/b.txt", "destination": f"{base}/c.txt", "overwrite": True})["success"]
        assert mcp_manager.call_tool(fs, "fs.delete_file", {"path": f"{base}/c.txt"})["success"]
        assert mcp_manager.call_tool(fs, "fs.delete_directory", {"path": base, "recursive": True})["success"]

        # path escape denied
        esc = mcp_manager.call_tool(fs, "fs.read_file", {"path": "../outside_mcp_test.txt"})
        assert esc["success"] is False
    finally:
        if abs_base.exists():
            shutil.rmtree(abs_base)


def test_terminal_git_database_and_task_memory_parity():
    servers = {s["name"]: s for s in mcp_manager.list_servers()}
    term = servers["terminal"]["id"]
    git = servers["git"]["id"]
    dbs = servers["database"]["id"]
    tm = servers["task_memory"]["id"]

    # terminal
    r = mcp_manager.call_tool(term, "terminal.execute", {"command": "echo MCP_P6"})
    assert r["success"] and "MCP_P6" in r["content"]["stdout"]
    cwd = mcp_manager.call_tool(term, "terminal.get_cwd", {})
    assert cwd["success"] and "cwd" in cwd["content"]

    # git
    st = mcp_manager.call_tool(git, "git.status", {})
    assert st["success"] and "exit_code" in st["content"]
    br = mcp_manager.call_tool(git, "git.current_branch", {})
    assert br["success"]

    # database
    lc = mcp_manager.call_tool(dbs, "db.list_connections", {})
    assert lc["success"] and "connections" in lc["content"]
    # inspect schema on a known db if present; tolerate structured failure but call must return
    ins = mcp_manager.call_tool(dbs, "db.inspect_schema", {"database": "nexus_ai.db"})
    assert "success" in ins

    # task/memory
    created = mcp_manager.call_tool(tm, "task.create", {"title": "p6 task", "status": "pending"})
    assert created["success"]
    tid = created["content"]["id"]
    got = mcp_manager.call_tool(tm, "task.get", {"id": tid})
    assert got["success"] and got["content"]["id"] == tid
    listed = mcp_manager.call_tool(tm, "task.list", {"limit": 5})
    assert listed["success"] and listed["content"]["count"] >= 1
    upd = mcp_manager.call_tool(tm, "task.set_status", {"id": tid, "status": "completed"})
    assert upd["success"] and upd["content"]["status"] == "completed"

    mem = mcp_manager.call_tool(tm, "memory.store", {"category": "test", "content": "phase6 memory item", "importance": 3})
    assert mem["success"]
    mid = mem["content"]["id"]
    srch = mcp_manager.call_tool(tm, "memory.search", {"query": "phase6", "limit": 10})
    assert srch["success"] and any(m["id"] == mid for m in srch["content"]["memories"])
    delm = mcp_manager.call_tool(tm, "memory.delete", {"id": mid})
    assert delm["success"]


def test_audit_redaction_and_persistence():
    name = _unique("audit")
    cmd = _stdio_server()
    token = "super-secret-token-value"
    s = mcp_manager.register_server({
        "name": name, "transport": "stdio", "endpoint": cmd[0], "args": cmd[1:],
        "auth_config": {"bearer_token": token}, "config": {"timeout_ms": 10000},
        "permissions": {"allow": ["read"]},
    })
    sid = s["id"]
    try:
        mcp_manager.connect(sid)
        mcp_manager.call_tool(sid, "echo", {"text": "secret-check", "api_key": "leakme"})
        events = mcp_manager.audit_log(limit=20, server_id=sid)
        assert events
        blob = json.dumps(events)
        assert token not in blob
        assert "leakme" not in blob
        # public server view should not expose raw auth
        pub = mcp_manager.get_server(sid)
        assert pub and pub.get("auth_configured") is True
        assert "super-secret-token-value" not in json.dumps(pub)
    finally:
        mcp_manager.delete_server(sid)
