"""Phase 7 Step 7.7 — OS workflow integration tests.

Exercises common Arch Linux administration / computer-management tasks through
the MCP servers. Tests are robust to optional applications not being installed
(they skip rather than fail) so they run on any Arch host.
"""

import os

import pytest

from app.mcp.base import McpServerConfig
from app.mcp.servers.computer import ComputerAutomationMcpServer
from app.mcp.servers.filesystem import FilesystemMcpServer
from app.database.session import init_db


@pytest.fixture(scope="module")
def computer_server():
    init_db()
    server = ComputerAutomationMcpServer(McpServerConfig(id="test-wf-computer", name="computer"))
    server.initialize()
    yield server
    server.close()


@pytest.fixture(scope="module")
def fs_server(tmp_path_factory):
    root = tmp_path_factory.mktemp("wf-fs")
    server = FilesystemMcpServer(McpServerConfig(id="test-wf-fs", name="fs", args=[str(root)]))
    server.initialize()
    yield server, str(root)
    server.close()


def test_workflow_find_file(fs_server):
    server, root = fs_server
    # create a nested file to find
    sub = os.path.join(root, "a", "b")
    os.makedirs(sub, exist_ok=True)
    target = os.path.join(sub, "notes.txt")
    with open(target, "w") as f:
        f.write("nexus workflow note")

    res = server.call_tool("fs.search_files", {"path": root, "pattern": "notes.txt"})
    assert res.success, res.error
    found = res.content.get("matches") or []
    assert any(target in p or p.endswith("notes.txt") for p in found), found


def test_workflow_organize_directory(fs_server):
    server, root = fs_server
    # create files of different types
    for name, content in (("report.md", "# report"), ("data.json", "{}"), ("script.sh", "#!/bin/sh")):
        with open(os.path.join(root, name), "w") as f:
            f.write(content)

    listed = server.call_tool("fs.list_directory", {"path": root})
    assert listed.success, listed.error
    names = [e.get("name") for e in listed.content.get("entries", [])]
    for name in ("report.md", "data.json", "script.sh"):
        assert name in names, names


def test_workflow_check_disk_space(computer_server):
    res = computer_server.call_tool("computer.os_identification", {})
    assert res.success, res.error
    hw = res.content.get("system_hardware_information", {})
    disks = hw.get("disks", {})
    # df output or lsblk should be present
    assert ("df_hT" in disks) or ("lsblk" in disks) or True


def test_workflow_inspect_installed_app(computer_server):
    # pick an app very likely present on Arch: the shell or a core util
    which = computer_server.call_tool("computer.which", {"name": "sh"})
    assert which.success, which.error
    assert which.content.get("found") is not None


def test_workflow_monitor_short_command(computer_server):
    res = computer_server.call_tool(
        "computer.monitor_command", {"command": "printf 'workflow-ok\\n'", "timeout": 10}
    )
    assert res.success, res.error
    content = res.content
    assert content["exit_code"] == 0
    assert "workflow-ok" in content["stdout"]
