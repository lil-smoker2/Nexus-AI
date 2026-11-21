"""Phase 7.4 pacman adapter tests: availability, search/info/deps, and mutating-op gating."""

import pytest

from app.mcp.base import McpServerConfig
from app.mcp.servers.pacman import PacmanMcpServer


@pytest.fixture(scope="module")
def pacman_server():
    server = PacmanMcpServer(McpServerConfig(id="test-pacman", name="pacman"))
    server.initialize()
    yield server
    server.close()


def test_pacman_availability(pacman_server):
    res = pacman_server.call_tool("pacman.is_available", {})
    assert res.success, res.error
    # pacman is expected on Arch Linux; skip if genuinely absent
    if not res.content["available"]:
        pytest.skip("pacman not available on this host")
    assert res.content["pacman"]


def test_pacman_search(pacman_server):
    avail = pacman_server.call_tool("pacman.is_available", {})
    if not avail.content["available"]:
        pytest.skip("pacman not available")
    res = pacman_server.call_tool("pacman.search", {"query": "firefox", "limit": 3})
    assert res.success, res.error
    assert "packages" in res.content and "count" in res.content


def test_pacman_info_and_dependencies(pacman_server):
    avail = pacman_server.call_tool("pacman.is_available", {})
    if not avail.content["available"]:
        pytest.skip("pacman not available")
    info = pacman_server.call_tool("pacman.info", {"package": "pacman"})
    assert info.success, info.error
    assert info.content["info"].get("Name") == "pacman"

    deps = pacman_server.call_tool("pacman.dependencies", {"package": "pacman"})
    assert deps.success, deps.error
    assert "depends_on" in deps.content


def test_pacman_list_installed(pacman_server):
    avail = pacman_server.call_tool("pacman.is_available", {})
    if not avail.content["available"]:
        pytest.skip("pacman not available")
    res = pacman_server.call_tool("pacman.list_installed", {"limit": 5})
    assert res.success, res.error
    assert res.content["count"] > 0
    first = res.content["packages"][0]
    assert "name" in first and "version" in first


def test_pacman_updates_check(pacman_server):
    avail = pacman_server.call_tool("pacman.is_available", {})
    if not avail.content["available"]:
        pytest.skip("pacman not available")
    res = pacman_server.call_tool("pacman.updates", {})
    assert res.success, res.error
    assert "updates" in res.content and "count" in res.content


def test_pacman_mutating_ops_require_approval_and_config(pacman_server):
    avail = pacman_server.call_tool("pacman.is_available", {})
    if not avail.content["available"]:
        pytest.skip("pacman not available")

    no_approval = pacman_server.call_tool("pacman.install", {"packages": ["firefox"]})
    assert no_approval.success is False
    assert "approved" in (no_approval.error or "").lower()

    with_approval = pacman_server.call_tool("pacman.install", {"packages": ["firefox"], "approved": True})
    assert with_approval.success is False
    assert "disabled" in (with_approval.error or "").lower()

    remove_denied = pacman_server.call_tool("pacman.remove", {"packages": ["firefox"], "approved": True})
    assert remove_denied.success is False
    assert "disabled" in (remove_denied.error or "").lower()

    update_denied = pacman_server.call_tool("pacman.update", {"approved": True})
    assert update_denied.success is False
    assert "disabled" in (update_denied.error or "").lower()