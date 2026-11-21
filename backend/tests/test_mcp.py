"""Smoke tests for MCP runtime (internal servers and tool calls)."""

from app.mcp.manager import mcp_manager
from app.database.session import init_db


def setup_module(module=None):
    init_db()
    # ensure fresh init
    mcp_manager.initialize()


def test_mcp_servers_registered_and_connected():
    servers = mcp_manager.list_servers()
    names = {s["name"] for s in servers}
    assert {"filesystem", "terminal", "git", "database", "browser", "computer", "task_memory"}.issubset(names)
    connected = {s["name"] for s in servers if s["status"] == "connected"}
    # all internal servers should auto-connect
    assert {"filesystem", "terminal", "git", "database", "browser", "computer", "task_memory"}.issubset(connected)


def test_filesystem_create_list_delete():
    servers = {s["name"]: s for s in mcp_manager.list_servers()}
    fs_id = servers["filesystem"]["id"]
    base = "tmp_mcp_test"
    # create directory and file
    r1 = mcp_manager.call_tool(fs_id, "fs.create_directory", {"path": base})
    assert r1["success"], r1
    r2 = mcp_manager.call_tool(fs_id, "fs.create_file", {"path": f"{base}/hello.txt", "content": "hello", "overwrite": True})
    assert r2["success"], r2
    # list
    r3 = mcp_manager.call_tool(fs_id, "fs.list_directory", {"path": base})
    assert r3["success"], r3
    names = [e["name"] for e in r3["content"]["entries"]]
    assert "hello.txt" in names
    # copy
    r4 = mcp_manager.call_tool(fs_id, "fs.copy_file", {"source": f"{base}/hello.txt", "destination": f"{base}/hello_copy.txt", "overwrite": True})
    assert r4["success"] and r4["content"]["destination_exists"]
    # delete file and dir
    r5 = mcp_manager.call_tool(fs_id, "fs.delete_file", {"path": f"{base}/hello.txt"})
    assert r5["success"] and r5["content"]["exists"] is False
    r6 = mcp_manager.call_tool(fs_id, "fs.delete_file", {"path": f"{base}/hello_copy.txt"})
    assert r6["success"]
    r7 = mcp_manager.call_tool(fs_id, "fs.delete_directory", {"path": base, "recursive": True})
    assert r7["success"] and r7["content"]["exists"] is False


def test_terminal_execute_and_git_status():
    servers = {s["name"]: s for s in mcp_manager.list_servers()}
    term = servers["terminal"]["id"]
    r = mcp_manager.call_tool(term, "terminal.execute", {"command": "echo MCP_OK"})
    assert r["success"], r
    assert "MCP_OK" in r["content"]["stdout"]
    git = servers["git"]["id"]
    g = mcp_manager.call_tool(git, "git.status", {})
    assert g["success"], g
    assert "exit_code" in g["content"]


def test_database_inspect_and_task_memory():
    servers = {s["name"]: s for s in mcp_manager.list_servers()}
    dbs = servers["database"]["id"]
    s = mcp_manager.call_tool(dbs, "db.inspect_schema", {"database": "nexus_ai.db"})
    # db may or may not exist depending on cwd; but call should return structured result
    assert "success" in s
    tm = servers["task_memory"]["id"]
    c = mcp_manager.call_tool(tm, "task.create", {"title": "MCP test task", "status": "pending"})
    assert c["success"], c
    tid = c["content"]["id"]
    l = mcp_manager.call_tool(tm, "task.list", {"limit": 10})
    assert l["success"], l
    g = mcp_manager.call_tool(tm, "task.get", {"id": tid})
    assert g["success"] and g["content"]["id"] == tid


def test_filesystem_step72_navigation_inspection_permissions_backup():
    """Phase 7.2: navigation, inspection, permissions inspection, backup."""
    servers = {s["name"]: s for s in mcp_manager.list_servers()}
    fs_id = servers["filesystem"]["id"]
    base = "tmp_mcp_step72"

    pwd = mcp_manager.call_tool(fs_id, "fs.pwd", {})
    assert pwd["success"], pwd
    assert "root" in pwd["content"] and "allowed_root" in pwd["content"]

    res = mcp_manager.call_tool(fs_id, "fs.resolve_path", {"path": f"{base}/../{base}/x"})
    assert res["success"], res
    assert res["content"]["within_root"] is True
    assert res["content"]["relative"].endswith(f"{base}/x")

    assert mcp_manager.call_tool(fs_id, "fs.create_directory", {"path": base})["success"]
    cf = mcp_manager.call_tool(fs_id, "fs.create_file", {"path": f"{base}/a.txt", "content": "step72-data", "overwrite": True})
    assert cf["success"], cf

    insp = mcp_manager.call_tool(fs_id, "fs.inspect_path", {"path": f"{base}/a.txt"})
    assert insp["success"] and insp["content"]["exists"] is True
    assert insp["content"]["type"] == "file"
    assert "permissions" in insp["content"]
    assert insp["content"].get("owner") or insp["content"].get("uid") is not None

    perms = mcp_manager.call_tool(fs_id, "fs.get_permissions", {"path": f"{base}/a.txt"})
    assert perms["success"], perms
    assert "mode_octal" in perms["content"]
    assert perms["content"].get("readable") in (True, False)

    st = mcp_manager.call_tool(fs_id, "fs.stat", {"path": base})
    assert st["success"] and st["content"]["is_dir"] is True and st["content"]["type"] == "directory"

    bk = mcp_manager.call_tool(fs_id, "fs.backup_path", {"path": f"{base}/a.txt"})
    assert bk["success"], bk
    assert bk["content"]["verified"] is True
    assert bk["content"]["source"].endswith(f"{base}/a.txt")
    backup_file = bk["content"]["backup"]
    # backup is readable copy
    br = mcp_manager.call_tool(fs_id, "fs.read_file", {"path": backup_file})
    assert br["success"] and "step72-data" in br["content"]["content"]

    # cleanup: delete backup and test dir
    assert mcp_manager.call_tool(fs_id, "fs.delete_file", {"path": backup_file})["success"]
    assert mcp_manager.call_tool(fs_id, "fs.delete_file", {"path": f"{base}/a.txt"})["success"]
    dd = mcp_manager.call_tool(fs_id, "fs.delete_directory", {"path": base, "recursive": True})
    assert dd["success"] and dd["content"]["exists"] is False
