"""Phase 7.3 OS agent tests: application control, windows, process inspection."""

import time

import pytest

from app.mcp.base import McpServerConfig
from app.mcp.servers.computer import ComputerAutomationMcpServer
from app.database.session import init_db


@pytest.fixture(scope="module")
def computer_server():
    init_db()
    server = ComputerAutomationMcpServer(McpServerConfig(id="test-computer", name="computer"))
    server.initialize()
    yield server
    server.close()


def test_capabilities_report_application_and_process_backends(computer_server):
    res = computer_server.call_tool("computer.capabilities", {})
    assert res.success, res.error
    caps = res.content["capabilities"]
    for key in ("launch_application", "process_inspection", "process_termination", "list_applications"):
        assert key in caps, key
    assert caps["process_inspection"]["supported"] is True
    assert caps["list_applications"]["supported"] is True


def test_application_discovery_search_and_info(computer_server, tmp_path, monkeypatch):
    desktop = tmp_path / "nexus-test.desktop"
    desktop.write_text(
        "[Desktop Entry]\nName=Nexus Test App\nExec=/bin/true\nIcon=utilities-terminal\nCategories=Utility;Test;\n",
        encoding="utf-8",
    )
    monkeypatch.setattr("app.mcp.servers.computer.DESKTOP_DIRS", [str(tmp_path)])

    listing = computer_server.call_tool("computer.list_applications", {"limit": 10})
    assert listing.success, listing.error
    assert listing.content["count"] == 1
    first = listing.content["applications"][0]
    assert first["id"].endswith(".desktop")
    assert first["name"] == "Nexus Test App"

    found = computer_server.call_tool("computer.find_application", {"query": "Nexus"})
    assert found.success, found.error
    assert found.content["count"] >= 1
    assert any(m["id"] == first["id"] for m in found.content["matches"])

    info = computer_server.call_tool("computer.application_info", {"desktop_file": first["desktop_file"]})
    assert info.success, info.error
    app = info.content["application"]
    assert app["desktop_file"] == first["desktop_file"]
    assert "exec" in app and "categories" in app
    assert "running" in info.content and "pids" in info.content["running"]


def test_process_name_matching_is_exact(computer_server):
    partial = computer_server.call_tool("computer.inspect_process", {"name": "sle"})
    assert partial.success, partial.error
    assert partial.content["pids"] == []


def test_filesystem_backup_refuses_root_escape(tmp_path):
    from app.mcp.servers.filesystem import FilesystemMcpServer

    root = tmp_path / "allowed"
    root.mkdir()
    server = FilesystemMcpServer(McpServerConfig(id="fs-root", name="fs", args=[str(root)]))
    server.initialize()
    try:
        res = server.call_tool("fs.backup_path", {"path": "."})
        assert res.success is False
        assert not any(p != root and p.name.startswith(root.name) for p in tmp_path.iterdir())
    finally:
        server.close()


def test_window_and_active_application_reporting(computer_server):
    windows = computer_server.call_tool("computer.list_windows", {})
    assert windows.success, windows.error
    assert "windows" in windows.content
    assert "supported" in windows.content and "source" in windows.content
    assert isinstance(windows.content["windows"], list)

    active = computer_server.call_tool("computer.active_application", {})
    assert active.success, active.error
    assert "active" in active.content
    assert "supported" in active.content
    assert "windows" in active.content


def test_launch_inspect_terminate_arbitrary_process(computer_server):
    denied = computer_server.call_tool(
        "computer.launch_application", {"app": "sleep 5", "allow_arbitrary": True}
    )
    assert denied.success is False
    assert "approved" in (denied.error or "").lower()

    launched = computer_server.call_tool(
        "computer.launch_application",
        {"app": "sleep 15", "allow_arbitrary": True, "approved": True},
    )
    assert launched.success, launched.error
    pid = launched.content["pid"]
    assert launched.content["method"] == "direct-exec"

    inspected = computer_server.call_tool("computer.inspect_process", {"pid": pid})
    assert inspected.success, inspected.error
    assert inspected.content["exists"] is True
    assert inspected.content["comm"] == "sleep"
    assert inspected.content["user"]
    assert inspected.content["cmdline"][-1] == "15"
    assert inspected.content["cgroup"]

    by_name = computer_server.call_tool("computer.inspect_process", {"name": "sleep"})
    assert by_name.success, by_name.error
    assert pid in by_name.content["pids"]

    no_approval = computer_server.call_tool("computer.terminate_process", {"pid": pid})
    assert no_approval.success is False

    critical = computer_server.call_tool(
        "computer.terminate_process", {"pid": 1, "approved": True}
    )
    assert critical.success is False
    assert critical.content["targets"][0]["ok"] is False

    terminated = computer_server.call_tool(
        "computer.terminate_process", {"pid": pid, "approved": True}
    )
    assert terminated.success, terminated.error
    assert terminated.content["sent"] == 1
    time.sleep(0.2)
    gone = computer_server.call_tool("computer.inspect_process", {"pid": pid})
    assert gone.content.get("exists") in (True, False)
    if gone.content.get("exists"):
        assert gone.content.get("state") in ("Z", "X")


def test_monitor_command_quick_command(computer_server):
    res = computer_server.call_tool(
        "computer.monitor_command", {"command": "echo hello-nexus", "timeout": 10}
    )
    assert res.success, res.error
    content = res.content
    assert content["exit_code"] == 0
    assert content["timed_out"] is False
    assert "hello-nexus" in content["stdout"]
    assert content["pid"] > 0
    assert content["duration_seconds"] >= 0


def test_monitor_command_timeout(computer_server):
    res = computer_server.call_tool(
        "computer.monitor_command", {"command": "sleep 30", "timeout": 2, "poll_interval": 0.5}
    )
    assert res.success is False or res.content["timed_out"] is True
    content = res.content
    assert content["timed_out"] is True
    assert content["exit_code"] is not None
    assert content["sample_count"] >= 0


def test_monitor_command_executable_not_found(computer_server):
    res = computer_server.call_tool(
        "computer.monitor_command", {"command": "definitely-not-a-real-nexus-binary xyz", "timeout": 5}
    )
    assert res.success is False
    assert "not found" in (res.error or "").lower()


def test_monitor_command_nonzero_exit(computer_server):
    res = computer_server.call_tool(
        "computer.monitor_command", {"command": "false", "timeout": 10}
    )
    assert res.success is False
    assert res.content["exit_code"] != 0
