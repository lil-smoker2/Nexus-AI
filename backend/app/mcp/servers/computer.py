"""Computer Automation MCP server: OS/session control primitives and adapter boundary.

Works on Arch Linux; on GNOME Wayland some UI automation is restricted by the
compositor/permissions. This server reports capabilities explicitly and delegates
desktop actions to available system tools/backends (service-adapter boundary).
"""

from __future__ import annotations

import getpass
import glob
import json
import os
import platform
import pwd
import re
import shlex
import shutil
import signal as signalmod
import subprocess
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from app.mcp.base import BaseMcpServer, McpServerConfig, ToolDefinition, ToolResult


CRITICAL_PROCESS_NAMES = {
    "systemd", "systemd-logind", "systemd-journal", "systemd-udevd", "dbus-daemon",
    "dbus-broker", "gnome-shell", "gnome-session-b", "gnome-session-c", "mutter",
    "Xorg", "Xwayland", "sshd", "gdm", "gdm3", "pipewire", "pipewire-pulse",
    "wireplumber", "init", "kthreadd",
}

DESKTOP_DIRS = ["/usr/share/applications", "/usr/local/share/applications",
                os.path.expanduser("~/.local/share/applications"),
                "/var/lib/flatpak/exports/share/applications",
                os.path.expanduser("~/.local/share/flatpak/exports/share/applications")]

ATSPI_WINDOWS_SCRIPT = r"""
import json, sys
try:
    import gi
    gi.require_version('Atspi', '2.0')
    from gi.repository import Atspi
except Exception as exc:
    print(json.dumps({"available": False, "error": str(exc)}))
    sys.exit(0)
out = []
try:
    desktop = Atspi.get_desktop(0)
    for i in range(desktop.get_child_count()):
        try:
            app = desktop.get_child_at_index(i)
            app_name = app.get_name()
            app_pid = None
            try:
                app_pid = app.get_process_id()
            except Exception:
                pass
            for j in range(app.get_child_count()):
                try:
                    frame = app.get_child_at_index(j)
                    role = frame.get_role_name()
                    if role not in ('frame', 'dialog', 'window'):
                        continue
                    states = frame.get_state_set()
                    extents = None
                    try:
                        e = frame.get_extents(Atspi.CoordType.SCREEN)
                        extents = [e.x, e.y, e.width, e.height]
                    except Exception:
                        pass
                    out.append({
                        "app": app_name,
                        "app_pid": app_pid,
                        "title": frame.get_name() or "",
                        "role": role,
                        "active": states.contains(Atspi.StateType.ACTIVE),
                        "focused": states.contains(Atspi.StateType.FOCUSED),
                        "extents": extents,
                    })
                except Exception:
                    continue
        except Exception:
            continue
    print(json.dumps({"available": True, "windows": out}))
except Exception as exc:
    print(json.dumps({"available": False, "error": str(exc)}))
"""


def _run(cmd: List[str], timeout: int = 10, input_text: Optional[str] = None) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, input=input_text)


def _read_text(path: str) -> Optional[str]:
    try:
        return Path(path).read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return None


def _parse_os_release() -> Dict[str, Any]:
    data: Dict[str, Any] = {}
    text = _read_text("/etc/os-release")
    if not text:
        return data
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        v = v.strip().strip('"').strip("'")
        data[k] = v
    return data


def _detect_package_managers() -> Dict[str, Any]:
    candidates = [
        ("pacman", ["pacman"]),
        ("yay", ["yay"]),
        ("paru", ["paru"]),
        ("flatpak", ["flatpak"]),
        ("snap", ["snap"]),
        ("apt", ["apt", "apt-get"]),
        ("dnf", ["dnf"]),
        ("yum", ["yum"]),
        ("zypper", ["zypper"]),
        ("rpm", ["rpm"]),
        ("dpkg", ["dpkg"]),
        ("brew", ["brew"]),
    ]
    installed = []
    paths: Dict[str, str] = {}
    for name, bins in candidates:
        found = None
        for b in bins:
            p = shutil.which(b)
            if p:
                found = p
                break
        if found:
            installed.append(name)
            paths[name] = found
    primary = None
    for pref in ("pacman", "apt", "dnf", "yum", "zypper"):
        if pref in installed:
            primary = pref
            break
    if not primary and installed:
        primary = installed[0]
    return {"primary": primary, "installed": installed, "paths": paths}


def _available_shells() -> Dict[str, Any]:
    shells = []
    text = _read_text("/etc/shells")
    if text:
        for line in text.splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                shells.append(line)
    current = os.environ.get("SHELL")
    existing = [s for s in shells if os.path.exists(s)]
    return {"current": current, "configured": shells, "available": existing or shells}


def _cpu_info() -> Dict[str, Any]:
    info: Dict[str, Any] = {"logical_cpus": os.cpu_count()}
    if shutil.which("lscpu"):
        try:
            p = _run(["lscpu"], timeout=5)
            if p.returncode == 0 and p.stdout:
                parsed: Dict[str, str] = {}
                for line in p.stdout.splitlines():
                    if ":" in line:
                        k, v = line.split(":", 1)
                        parsed[k.strip()] = v.strip()
                for key, out in [
                    ("Architecture", "architecture"),
                    ("Model name", "model_name"),
                    ("Vendor ID", "vendor"),
                    ("CPU(s)", "cpus"),
                    ("Thread(s) per core", "threads_per_core"),
                    ("Core(s) per socket", "cores_per_socket"),
                    ("Socket(s)", "sockets"),
                ]:
                    if key in parsed:
                        info[out] = parsed[key]
                info["lscpu"] = parsed
        except Exception:
            pass
    # fallback to /proc/cpuinfo model name
    if "model_name" not in info:
        text = _read_text("/proc/cpuinfo") or ""
        for line in text.splitlines():
            if line.lower().startswith("model name") and ":" in line:
                info["model_name"] = line.split(":", 1)[1].strip()
                break
    return info


def _memory_info() -> Dict[str, Any]:
    info: Dict[str, Any] = {}
    text = _read_text("/proc/meminfo") or ""
    for line in text.splitlines():
        if ":" not in line:
            continue
        k, v = line.split(":", 1)
        if k in ("MemTotal", "MemFree", "MemAvailable", "SwapTotal", "SwapFree", "Buffers", "Cached"):
            info[k] = v.strip()
    if shutil.which("free"):
        try:
            p = _run(["free", "-h"], timeout=5)
            if p.returncode == 0:
                info["free_h"] = p.stdout.strip().splitlines()
        except Exception:
            pass
    return info


def _disk_info() -> Dict[str, Any]:
    info: Dict[str, Any] = {}
    if shutil.which("lsblk"):
        try:
            p = _run(["lsblk", "-o", "NAME,SIZE,TYPE,MOUNTPOINTS,FSTYPE,MODEL", "-J"], timeout=5)
            if p.returncode == 0 and p.stdout:
                try:
                    info["lsblk"] = json.loads(p.stdout)
                except Exception:
                    info["lsblk_raw"] = p.stdout.strip().splitlines()[:50]
        except Exception:
            pass
    if shutil.which("df"):
        try:
            p = _run(["df", "-hT"], timeout=5)
            if p.returncode == 0:
                info["df_hT"] = p.stdout.strip().splitlines()[:40]
        except Exception:
            pass
    return info


def _hostname_info() -> Dict[str, Any]:
    info: Dict[str, Any] = {}
    try:
        info["hostname"] = platform.node() or os.uname().nodename
    except Exception:
        pass
    if shutil.which("hostnamectl"):
        try:
            p = _run(["hostnamectl", "--json=short"], timeout=5)
            if p.returncode == 0 and p.stdout:
                try:
                    info["hostnamectl"] = json.loads(p.stdout)
                except Exception:
                    p2 = _run(["hostnamectl"], timeout=5)
                    if p2.returncode == 0:
                        info["hostnamectl_text"] = p2.stdout.strip().splitlines()[:30]
        except Exception:
            pass
    return info


def _hardware_info() -> Dict[str, Any]:
    hw: Dict[str, Any] = {}
    hw["cpu"] = _cpu_info()
    hw["memory"] = _memory_info()
    hw["disks"] = _disk_info()
    hw["hostname"] = _hostname_info()
    if shutil.which("uname"):
        try:
            p = _run(["uname", "-a"], timeout=5)
            if p.returncode == 0:
                hw["uname_a"] = p.stdout.strip()
        except Exception:
            pass
    try:
        hw["uptime_seconds"] = float(Path("/proc/uptime").read_text().split()[0])
    except Exception:
        pass
    return hw


def collect_os_identification() -> Dict[str, Any]:
    os_release = _parse_os_release()
    try:
        uname = os.uname()
        kernel = uname.release
        kernel_version = uname.version
        uname_info = {
            "sysname": uname.sysname,
            "nodename": uname.nodename,
            "release": uname.release,
            "version": uname.version,
            "machine": uname.machine,
        }
    except Exception:
        kernel = platform.release()
        kernel_version = platform.version()
        uname_info = {"release": kernel, "version": kernel_version, "machine": platform.machine()}

    distribution = {
        "name": os_release.get("NAME") or os_release.get("ID") or platform.system(),
        "pretty_name": os_release.get("PRETTY_NAME") or os_release.get("NAME") or platform.platform(),
        "id": os_release.get("ID"),
        "id_like": os_release.get("ID_LIKE"),
        "version_id": os_release.get("VERSION_ID"),
        "version": os_release.get("VERSION"),
        "build_id": os_release.get("BUILD_ID"),
        "home_url": os_release.get("HOME_URL"),
        "raw": os_release,
    }

    desktop_environment = os.environ.get("XDG_CURRENT_DESKTOP") or os.environ.get("DESKTOP_SESSION") or os.environ.get("XDG_SESSION_DESKTOP")
    session_type = os.environ.get("XDG_SESSION_TYPE")
    user = {
        "name": getpass.getuser() if hasattr(getpass, "getuser") else os.environ.get("USER") or os.environ.get("LOGNAME"),
        "uid": os.getuid() if hasattr(os, "getuid") else None,
        "gid": os.getgid() if hasattr(os, "getgid") else None,
        "home": os.path.expanduser("~"),
    }

    return {
        "distribution": distribution,
        "kernel": {"release": kernel, "version": kernel_version, "uname": uname_info},
        "architecture": platform.machine() or uname_info.get("machine"),
        "desktop_environment": desktop_environment,
        "session_type": session_type,
        "logged_in_user": user,
        "installed_package_manager": _detect_package_managers(),
        "available_shell": _available_shells(),
        "system_hardware_information": _hardware_info(),
        "platform": {
            "system": platform.system(),
            "platform": platform.platform(),
            "python_version": platform.python_version(),
        },
    }


class ComputerAutomationMcpServer(BaseMcpServer):
    server_type = "computer"

    def __init__(self, config: McpServerConfig):
        super().__init__(config)
        self._register_tools()

    def _register_tools(self) -> None:
        t = self.register_tool
        # Info / discovery
        t(ToolDefinition("computer.get_session_info", "Get OS and session info", {"type": "object", "properties": {}}, "read"), self.get_session_info)
        t(ToolDefinition("computer.os_identification", "Retrieve structured OS identification (distribution, kernel, architecture, desktop, session, user, package managers, shells, hardware)", {"type": "object", "properties": {}}, "read"), self.os_identification)
        t(ToolDefinition("computer.capabilities", "Report supported OS-control capabilities and Wayland/compositor limitations", {"type": "object", "properties": {}}, "read"), self.capabilities)
        t(ToolDefinition("computer.list_processes", "List running processes (top)", {"type": "object", "properties": {"limit": {"type": "integer"}}}, "read"), self.list_processes)
        t(ToolDefinition("computer.which", "Locate an executable", {"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]}, "read"), self.which)
        t(ToolDefinition("computer.list_applications", "List installed desktop applications", {"type": "object", "properties": {"limit": {"type": "integer"}, "include_hidden": {"type": "boolean"}}}, "read"), self.list_applications)
        t(ToolDefinition("computer.find_application", "Search installed desktop applications by name/id/keywords/categories", {"type": "object", "properties": {"query": {"type": "string"}, "limit": {"type": "integer"}}, "required": ["query"]}, "read"), self.find_application)
        t(ToolDefinition("computer.application_info", "Inspect an installed application (desktop entry, exec, categories, running state)", {"type": "object", "properties": {"app": {"type": "string"}, "desktop_file": {"type": "string"}}, "required": []}, "read"), self.application_info)
        t(ToolDefinition("computer.list_windows", "List desktop windows using available backends (AT-SPI/X11/wlroots)", {"type": "object", "properties": {"include_hidden": {"type": "boolean"}}}, "read"), self.list_windows)
        t(ToolDefinition("computer.active_application", "Identify the active application/window if the session backend exposes it", {"type": "object", "properties": {}}, "read"), self.active_application)
        t(ToolDefinition("computer.inspect_process", "Inspect a process by pid or name (cmdline, owner, memory, state, cgroup)", {"type": "object", "properties": {"pid": {"type": "integer"}, "name": {"type": "string"}}, "required": []}, "read"), self.inspect_process)
        t(ToolDefinition("computer.launch_application", "Launch an installed desktop application or (with allow_arbitrary) an executable", {"type": "object", "properties": {"app": {"type": "string"}, "args": {"type": "array", "items": {"type": "string"}}, "allow_arbitrary": {"type": "boolean"}, "approved": {"type": "boolean"}}, "required": ["app"]}, "execute"), self.launch_application)
        t(ToolDefinition("computer.terminate_process", "Terminate a process by pid or name (destructive; requires approved=true)", {"type": "object", "properties": {"pid": {"type": "integer"}, "name": {"type": "string"}, "signal": {"type": "string"}, "all_matches": {"type": "boolean"}, "approved": {"type": "boolean"}, "allow_critical": {"type": "boolean"}}, "required": []}, "destructive"), self.terminate_process)
        # Open / launch / notify
        t(ToolDefinition("computer.open_path", "Open a file or path with the default handler (xdg-open)", {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}, "execute"), self.open_path)
        t(ToolDefinition("computer.open_uri", "Open a URL or URI with the default handler (xdg-open/gio)", {"type": "object", "properties": {"uri": {"type": "string"}}, "required": ["uri"]}, "execute"), self.open_uri)
        t(ToolDefinition("computer.notify", "Send a desktop notification", {"type": "object", "properties": {"title": {"type": "string"}, "body": {"type": "string"}, "urgency": {"type": "string"}}, "required": ["title"]}, "execute"), self.notify)
        # GNOME / D-Bus integration
        t(ToolDefinition("computer.dbus_list_names", "List session D-Bus names (optionally filtered)", {"type": "object", "properties": {"filter": {"type": "string"}, "limit": {"type": "integer"}}}, "read"), self.dbus_list_names)
        t(ToolDefinition("computer.dbus_introspect", "Introspect a D-Bus service/object", {"type": "object", "properties": {"destination": {"type": "string"}, "object_path": {"type": "string"}}, "required": ["destination"]}, "read"), self.dbus_introspect)
        t(ToolDefinition("computer.gio_info", "Get GIO/GVFS file info for a path", {"type": "object", "properties": {"path": {"type": "string"}, "attributes": {"type": "string"}}, "required": ["path"]}, "read"), self.gio_info)
        t(ToolDefinition("computer.gnome_session_info", "Get GNOME session/desktop integration details", {"type": "object", "properties": {}}, "read"), self.gnome_session_info)
        # Audio
        t(ToolDefinition("computer.audio_get", "Get default sink volume/mute state (pactl)", {"type": "object", "properties": {}}, "read"), self.audio_get)
        t(ToolDefinition("computer.audio_set_volume", "Set default sink volume (e.g. 50%, +5%, -5%)", {"type": "object", "properties": {"volume": {"type": "string"}}, "required": ["volume"]}, "execute"), self.audio_set_volume)
        t(ToolDefinition("computer.audio_set_mute", "Mute/unmute/toggle default sink", {"type": "object", "properties": {"mute": {"type": ["boolean", "string"]}}, "required": ["mute"]}, "execute"), self.audio_set_mute)
        # Brightness
        t(ToolDefinition("computer.brightness_get", "Get display brightness (brightnessctl)", {"type": "object", "properties": {}}, "read"), self.brightness_get)
        t(ToolDefinition("computer.brightness_set", "Set display brightness (e.g. 50%, +10%, 200)", {"type": "object", "properties": {"value": {"type": "string"}}, "required": ["value"]}, "execute"), self.brightness_set)
        # Media
        t(ToolDefinition("computer.media_status", "Get media player status (playerctl)", {"type": "object", "properties": {}}, "read"), self.media_status)
        t(ToolDefinition("computer.media_control", "Control media player (play/pause/play-pause/next/previous/stop)", {"type": "object", "properties": {"action": {"type": "string"}, "player": {"type": "string"}}, "required": ["action"]}, "execute"), self.media_control)
        # Clipboard
        t(ToolDefinition("computer.clipboard_get", "Read clipboard text (wl-paste on Wayland)", {"type": "object", "properties": {}}, "read"), self.clipboard_get)
        t(ToolDefinition("computer.clipboard_set", "Write clipboard text (wl-copy on Wayland)", {"type": "object", "properties": {"text": {"type": "string"}}, "required": ["text"]}, "execute"), self.clipboard_set)
        # UI automation (may be restricted)
        t(ToolDefinition("computer.screenshot", "Capture a screenshot to a file if compositor/permissions allow", {"type": "object", "properties": {"path": {"type": "string"}}, "required": []}, "execute"), self.screenshot)
        t(ToolDefinition("computer.input_text", "Type text via virtual keyboard if supported by compositor", {"type": "object", "properties": {"text": {"type": "string"}}, "required": ["text"]}, "execute"), self.input_text)

    # ---- helpers ----
    def _session(self) -> Dict[str, Any]:
        return {
            "platform": platform.platform(),
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
            "desktop": os.getenv("XDG_CURRENT_DESKTOP"),
            "session_type": os.getenv("XDG_SESSION_TYPE"),
            "display": os.getenv("DISPLAY"),
            "wayland_display": os.getenv("WAYLAND_DISPLAY"),
        }

    # ---- info ----
    def get_session_info(self, args: Dict[str, Any]) -> ToolResult:
        info = self._session()
        info.update({
            "python": platform.python_version(),
            "cwd": os.getcwd(),
            "user": os.getenv("USER") or os.getenv("USERNAME"),
            "home": os.path.expanduser("~"),
        })
        try:
            ident = collect_os_identification()
            # include key identification fields for convenience/back-compat
            info["os_identification"] = {
                "distribution": ident.get("distribution", {}).get("pretty_name"),
                "kernel": ident.get("kernel", {}).get("release"),
                "architecture": ident.get("architecture"),
                "desktop_environment": ident.get("desktop_environment"),
                "session_type": ident.get("session_type"),
                "package_manager": (ident.get("installed_package_manager") or {}).get("primary"),
                "shell": (ident.get("available_shell") or {}).get("current"),
            }
        except Exception:
            pass
        return ToolResult(success=True, content=info)

    def os_identification(self, args: Dict[str, Any]) -> ToolResult:
        try:
            data = collect_os_identification()
            return ToolResult(success=True, content=data)
        except Exception as e:
            return ToolResult(success=False, error=str(e), content={})

    def capabilities(self, args: Dict[str, Any]) -> ToolResult:
        sess = self._session()
        caps: Dict[str, Any] = {}
        caps["open_uri"] = {"supported": bool(shutil.which("xdg-open") or shutil.which("gio"))}
        caps["notify"] = {"supported": bool(shutil.which("notify-send"))}
        caps["audio"] = {"supported": bool(shutil.which("pactl"))}
        caps["brightness"] = {"supported": bool(shutil.which("brightnessctl"))}
        caps["media"] = {"supported": bool(shutil.which("playerctl"))}
        caps["clipboard"] = {"supported": bool(shutil.which("wl-copy") and shutil.which("wl-paste"))}
        caps["process_list"] = {"supported": bool(shutil.which("ps")), "backend": "ps" if shutil.which("ps") else None}
        caps["process_inspection"] = {"supported": os.path.isdir("/proc"), "backend": "/proc" if os.path.isdir("/proc") else None}
        caps["process_termination"] = {"supported": hasattr(os, "kill"), "note": "Destructive; requires approval/policy"}
        caps["list_applications"] = {"supported": True, "backend": "desktop-entries"}
        caps["launch_application"] = {"supported": bool(shutil.which("gtk-launch") or shutil.which("gio") or shutil.which("xdg-open")), "backend": "gtk-launch/gio" if (shutil.which("gtk-launch") or shutil.which("gio")) else "desktop Exec"}
        win_backends = self._window_backends()
        atspi = _atspi_windows()
        caps["window_inspection"] = {
            "supported": bool(win_backends or atspi.get("available")),
            "backends": win_backends + (["at-spi"] if atspi.get("available") else []),
            "at_spi_error": atspi.get("error") if not atspi.get("available") else None,
        }
        caps["active_application"] = {
            "supported": bool(win_backends or atspi.get("available")),
            "note": "Focus reporting depends on compositor/AT-SPI support",
        }
        caps["screenshot"] = {"supported": bool(shutil.which("grim")), "reason": "grim requires compositor screencopy support/permissions" if shutil.which("grim") else "No screenshot backend (grim/portal) available"}
        caps["input_injection"] = {"supported": bool(shutil.which("wtype") or shutil.which("ydotool")), "reason": "Virtual input requires supported compositor/tool permissions"}
        notes = []
        if sess.get("session_type") == "wayland":
            notes.append("Wayland session: screenshot/input/window control depend on compositor permissions and available backends; capability results reflect this host.")
        notes.append("Desktop UI automation is exposed via capability-gated adapters; configure portal/AT-SPI/input backends for deeper control where permitted.")
        return ToolResult(success=True, content={"session": sess, "capabilities": caps, "notes": notes, "works_on_arch_linux": True, "adapter": "system-tools"})

    def list_processes(self, args: Dict[str, Any]) -> ToolResult:
        limit = int(args.get("limit", 30))
        try:
            proc = _run(["ps", "-eo", "pid,comm,%cpu,%mem", "--sort=-%cpu"], timeout=10)
            if proc.returncode != 0:
                return ToolResult(success=False, error=proc.stderr.strip() or "ps failed")
            lines = proc.stdout.strip().splitlines()
            head = lines[:1]
            body = lines[1: 1 + max(1, min(limit, 200))]
            return ToolResult(success=True, content={"header": head[0] if head else "", "processes": body, "count": len(body)})
        except Exception as e:
            return ToolResult(success=False, error=str(e))

    def which(self, args: Dict[str, Any]) -> ToolResult:
        name = str(args.get("name", "")).strip()
        if not name:
            return ToolResult(success=False, error="name is required")
        path = shutil.which(name)
        return ToolResult(success=True, content={"name": name, "path": path, "found": path is not None})

    def _parse_desktop(self, path: str) -> Optional[Dict[str, Any]]:
        try:
            name = exec_cmd = icon = None
            fields: Dict[str, str] = {}
            localized: Dict[str, str] = {}
            in_entry = False
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                for raw in f:
                    line = raw.strip()
                    if line == "[Desktop Entry]":
                        in_entry = True
                        continue
                    if line.startswith("[") and line.endswith("]"):
                        if in_entry:
                            break
                        continue
                    if not in_entry or "=" not in line:
                        continue
                    k, v = line.split("=", 1)
                    if k.startswith("Name["):
                        localized[k] = v
                        continue
                    if k not in fields:
                        fields[k] = v
                    if k == "Name" and name is None:
                        name = v
                    elif k == "Exec" and exec_cmd is None:
                        exec_cmd = v
                    elif k == "Icon" and icon is None:
                        icon = v
            if not name:
                return None
            no_display = str(fields.get("NoDisplay", "")).strip().lower() in ("true", "1")
            return {
                "name": name,
                "exec": exec_cmd or "",
                "icon": icon or "",
                "desktop_file": path,
                "id": os.path.basename(path),
                "comment": fields.get("Comment"),
                "categories": [c for c in (fields.get("Categories") or "").split(";") if c],
                "keywords": [k for k in (fields.get("Keywords") or "").split(";") if k],
                "mime_types": [m for m in (fields.get("MimeType") or "").split(";") if m],
                "terminal": str(fields.get("Terminal", "")).strip().lower() in ("true", "1"),
                "type": fields.get("Type"),
                "path": fields.get("Path"),
                "try_exec": fields.get("TryExec"),
                "startup_wm_class": fields.get("StartupWMClass"),
                "dbus_activatable": str(fields.get("DBusActivatable", "")).strip().lower() in ("true", "1"),
                "no_display": no_display,
                "localized_names": localized,
            }
        except Exception:
            return None

    def _all_applications(self, include_hidden: bool = False, limit: int = 2000) -> List[Dict[str, Any]]:
        seen = set()
        apps: List[Dict[str, Any]] = []
        for d in DESKTOP_DIRS:
            if not os.path.isdir(d):
                continue
            for p in sorted(glob.glob(os.path.join(d, "*.desktop"))):
                app = self._parse_desktop(p)
                if not app:
                    continue
                key = app["id"]
                if key in seen:
                    continue
                seen.add(key)
                if app.get("no_display") and not include_hidden:
                    continue
                apps.append(app)
                if len(apps) >= limit:
                    return apps
        return apps

    def list_applications(self, args: Dict[str, Any]) -> ToolResult:
        limit = max(1, min(int(args.get("limit", 100)), 2000))
        include_hidden = bool(args.get("include_hidden", False))
        apps = self._all_applications(include_hidden=include_hidden, limit=limit)
        return ToolResult(success=True, content={"applications": apps, "count": len(apps), "include_hidden": include_hidden})

    def _match_apps(self, query: str, include_hidden: bool = True) -> List[Dict[str, Any]]:
        q = query.strip().lower()
        if not q:
            return []
        apps = self._all_applications(include_hidden=include_hidden)
        exact = []
        partial = []
        for app in apps:
            app_id = str(app.get("id", "")).lower()
            app_id_nostrip = app_id[:-8] if app_id.endswith(".desktop") else app_id
            name = str(app.get("name", "")).lower()
            exec_base = os.path.basename(_exec_program(app.get("exec", ""))).lower()
            hay = " ".join([
                app_id, app_id_nostrip, name, exec_base,
                " ".join(app.get("keywords") or []),
                " ".join(app.get("categories") or []),
                str(app.get("comment") or ""),
            ]).lower()
            if q in (app_id, app_id_nostrip, name, exec_base):
                exact.append(app)
            elif q in hay:
                partial.append(app)
        return exact + partial

    def find_application(self, args: Dict[str, Any]) -> ToolResult:
        query = str(args.get("query", "")).strip()
        if not query:
            return ToolResult(success=False, error="query is required")
        limit = max(1, min(int(args.get("limit", 20)), 200))
        matches = self._match_apps(query)[:limit]
        return ToolResult(success=True, content={"query": query, "matches": matches, "count": len(matches)})

    def application_info(self, args: Dict[str, Any]) -> ToolResult:
        target = str(args.get("app") or "").strip()
        desktop_file = str(args.get("desktop_file") or "").strip()
        app: Optional[Dict[str, Any]] = None
        if desktop_file:
            if not os.path.isfile(desktop_file):
                return ToolResult(success=False, error=f"Desktop file not found: {desktop_file}")
            app = self._parse_desktop(desktop_file)
        elif target:
            matches = self._match_apps(target)
            if not matches:
                return ToolResult(success=False, error=f"Application not found: {target}")
            app = matches[0]
        else:
            return ToolResult(success=False, error="app or desktop_file is required")
        if not app:
            return ToolResult(success=False, error="Could not parse desktop entry")
        running = self._app_running(app)
        return ToolResult(success=True, content={"application": app, "running": running})

    def _proc_pids_for_name(self, name: str) -> List[int]:
        needle = name.strip().lower()
        if not needle:
            return []
        pids: List[int] = []
        for entry in os.listdir("/proc"):
            if not entry.isdigit():
                continue
            pid = int(entry)
            try:
                comm = Path(f"/proc/{pid}/comm").read_text(encoding="utf-8", errors="ignore").strip()
            except Exception:
                continue
            if comm.lower() == needle:
                pids.append(pid)
                continue
            try:
                argv = [p for p in Path(f"/proc/{pid}/cmdline").read_bytes().split(b"\x00") if p]
            except Exception:
                continue
            if not argv:
                continue
            try:
                argv0 = argv[0].decode("utf-8", "ignore").lower()
            except Exception:
                continue
            if os.path.basename(argv0) == needle:
                pids.append(pid)
        return sorted(set(pids))

    def _app_running(self, app: Dict[str, Any]) -> Dict[str, Any]:
        program = _exec_program(app.get("exec", ""))
        base = os.path.basename(program) if program else ""
        wm_class = str(app.get("startup_wm_class") or "")
        candidates: List[str] = []
        for c in (base, wm_class):
            if c and c not in candidates:
                candidates.append(c)
        pids: List[int] = []
        for c in candidates:
            pids.extend(self._proc_pids_for_name(c))
        pids = sorted(set(pids))
        return {"running": bool(pids), "pids": pids, "matched": candidates}

    def _window_backends(self) -> List[str]:
        return [b for b in ("wmctrl", "swaymsg", "hyprctl") if shutil.which(b)]

    def _list_windows_backend(self) -> Tuple[List[Dict[str, Any]], Optional[str], List[str]]:
        windows: List[Dict[str, Any]] = []
        errors: List[str] = []
        if shutil.which("wmctrl"):
            try:
                p = _run(["wmctrl", "-l", "-p"], timeout=8)
                if p.returncode == 0:
                    for line in p.stdout.splitlines():
                        parts = line.split(None, 4)
                        if len(parts) >= 5:
                            windows.append({"id": parts[0], "desktop": parts[1], "pid": int(parts[2]) if parts[2].isdigit() else None, "host": parts[3], "title": parts[4], "source": "wmctrl"})
                    if windows:
                        return windows, "wmctrl", errors
                else:
                    errors.append(p.stderr.strip() or "wmctrl failed")
            except Exception as e:
                errors.append(f"wmctrl: {e}")
        if shutil.which("swaymsg"):
            try:
                p = _run(["swaymsg", "-t", "get_tree", "-r"], timeout=8)
                if p.returncode == 0 and p.stdout.strip():
                    tree = json.loads(p.stdout)
                    stack = [tree]
                    while stack:
                        node = stack.pop()
                        if not isinstance(node, dict):
                            continue
                        if node.get("type") in ("con", "floating_con") and node.get("name"):
                            windows.append({
                                "id": node.get("id"), "app": node.get("app_id"), "title": node.get("name"),
                                "focused": bool(node.get("focused")), "pid": node.get("pid"),
                                "workspace": (node.get("workspace") or {}).get("name") if isinstance(node.get("workspace"), dict) else None,
                                "source": "sway",
                            })
                        stack.extend(node.get("nodes") or [])
                        stack.extend(node.get("floating_nodes") or [])
                    if windows:
                        return windows, "sway", errors
            except Exception as e:
                errors.append(f"swaymsg: {e}")
        if shutil.which("hyprctl"):
            try:
                p = _run(["hyprctl", "clients", "-j"], timeout=8)
                if p.returncode == 0 and p.stdout.strip():
                    for c in json.loads(p.stdout):
                        windows.append({"id": c.get("address"), "app": c.get("class"), "title": c.get("title"), "pid": c.get("pid"), "workspace": (c.get("workspace") or {}).get("name") if isinstance(c.get("workspace"), dict) else None, "focused": bool(c.get("focusHistoryID") == 0), "source": "hyprland"})
                    if windows:
                        return windows, "hyprland", errors
            except Exception as e:
                errors.append(f"hyprctl: {e}")
        return windows, None, errors

    def list_windows(self, args: Dict[str, Any]) -> ToolResult:
        windows, source, errors = self._list_windows_backend()
        if not windows:
            atspi = _atspi_windows()
            if atspi.get("available"):
                windows = atspi.get("windows") or []
                source = "at-spi"
            elif atspi.get("error"):
                errors.append(f"at-spi: {atspi.get('error')}")
        return ToolResult(
            success=True,
            content={
                "windows": windows,
                "count": len(windows),
                "source": source,
                "supported": bool(source),
                "backends": self._window_backends() + (["at-spi"] if source == "at-spi" else []),
                "errors": errors,
                "session": self._session(),
            },
        )

    def active_application(self, args: Dict[str, Any]) -> ToolResult:
        active: Optional[Dict[str, Any]] = None
        windows, source, errors = self._list_windows_backend()
        if not windows:
            atspi = _atspi_windows()
            if atspi.get("available"):
                windows = atspi.get("windows") or []
                source = "at-spi"
            elif atspi.get("error"):
                errors.append(f"at-spi: {atspi.get('error')}")
        focused = [w for w in windows if w.get("focused")]
        if focused:
            active = focused[0]
        # AT-SPI often reports only the shell stage as focused on Wayland; do not
        # claim it is the user's active app.
        if active and str(active.get("app", "")).lower() in ("gnome-shell", "mutter"):
            active = None
            errors.append("AT-SPI focus is limited to the GNOME Shell stage on this session")
        if not active:
            # GNOME Shell Eval is usually disabled; try it as a best-effort backend.
            if shutil.which("gdbus"):
                try:
                    expr = "global.display.focus_window ? [global.display.focus_window.get_wm_class(), global.display.focus_window.get_title()] : null"
                    p = _run(["gdbus", "call", "--session", "--dest", "org.gnome.Shell", "--object-path", "/org/gnome/Shell", "--method", "org.gnome.Shell.Eval", expr], timeout=5)
                    out = p.stdout.strip()
                    match = re.match(r"^\(true,\s*'(.*?)'\)\s*$", out, re.S)
                    if match:
                        payload = match.group(1)
                        if payload not in ("null", "None", ""):
                            normalized = payload.replace("\\'", "'")
                            values = re.findall(r"'([^']*)'", normalized)
                            if values:
                                active = {
                                    "app": values[0] or None,
                                    "title": values[1] if len(values) > 1 else None,
                                    "raw": out,
                                    "source": "gnome-shell-eval",
                                }
                except Exception as e:
                    errors.append(f"gnome-shell-eval: {e}")
        return ToolResult(
            success=True,
            content={
                "active": active,
                "supported": bool(active),
                "windows": windows,
                "source": (active or {}).get("source") or source,
                "errors": errors,
                "session": self._session(),
                "note": None if active else "Active-window identification is not exposed by this compositor/session backend",
            },
        )

    # ---- process inspection / termination ----
    def _proc_info(self, pid: int) -> Dict[str, Any]:
        base = Path(f"/proc/{pid}")
        if not base.is_dir():
            return {"pid": pid, "exists": False}
        info: Dict[str, Any] = {"pid": pid, "exists": True}
        try:
            info["comm"] = (base / "comm").read_text(encoding="utf-8", errors="ignore").strip()
        except Exception:
            info["comm"] = None
        try:
            raw = (base / "cmdline").read_bytes()
            info["cmdline"] = [p for p in raw.split(b"\x00") if p]
            info["cmdline"] = [p.decode("utf-8", "ignore") for p in info["cmdline"]]
        except Exception:
            info["cmdline"] = []
        for key, out in (("exe", "exe"), ("cwd", "cwd"), ("root", "root")):
            try:
                info[out] = os.readlink(base / key)
            except Exception:
                info[out] = None
        status: Dict[str, str] = {}
        try:
            for line in (base / "status").read_text(encoding="utf-8", errors="ignore").splitlines():
                if ":" in line:
                    k, v = line.split(":", 1)
                    status[k.strip()] = v.strip()
        except Exception:
            pass
        for src, dst in (("Name", "name"), ("State", "state"), ("PPid", "ppid"), ("Uid", "uid"), ("Gid", "gid"),
                         ("Threads", "threads"), ("VmRSS", "vm_rss"), ("VmSize", "vm_size"), ("VmPeak", "vm_peak"),
                         ("VmSwap", "vm_swap"), ("Tgid", "tgid")):
            if src in status:
                info[dst] = status[src]
        if "ppid" in info:
            try:
                info["ppid"] = int(info["ppid"])
            except Exception:
                pass
        if "uid" in info:
            uid_parts = str(info["uid"]).split()
            try:
                uid = int(uid_parts[0])
                info["uid_num"] = uid
                info["user"] = pwd.getpwuid(uid).pw_name
            except Exception:
                pass
        try:
            stat_fields = (base / "stat").read_text(encoding="utf-8", errors="ignore").rsplit(")", 1)[1].split()
            # fields after comm: state ppid pgrp session tty tpgid flags minflt cminflt majflt cmajflt utime stime ...
            if len(stat_fields) > 19:
                info["state"] = stat_fields[0]
                info["utime_ticks"] = int(stat_fields[11])
                info["stime_ticks"] = int(stat_fields[12])
                start_ticks = int(stat_fields[19])
                try:
                    hz = os.sysconf("SC_CLK_TCK") or 100
                    btime = 0
                    for line in Path("/proc/stat").read_text(encoding="utf-8", errors="ignore").splitlines():
                        if line.startswith("btime "):
                            btime = int(line.split()[1]); break
                    if btime:
                        started = datetime.fromtimestamp(btime + start_ticks / hz, tz=timezone.utc)
                        info["started_at"] = started.isoformat()
                        info["uptime_seconds"] = int(time.time() - started.timestamp())
                except Exception:
                    pass
        except Exception:
            pass
        try:
            info["cgroup"] = (base / "cgroup").read_text(encoding="utf-8", errors="ignore").strip()
        except Exception:
            pass
        try:
            oom = (base / "oom_score").read_text(encoding="utf-8", errors="ignore").strip()
            if oom:
                info["oom_score"] = int(oom)
        except Exception:
            pass
        children = []
        for entry in os.listdir("/proc"):
            if not entry.isdigit():
                continue
            cpid = int(entry)
            try:
                stat = Path(f"/proc/{cpid}/stat").read_text(encoding="utf-8", errors="ignore")
                ppid = int(stat.rsplit(")", 1)[1].split()[1])
                if ppid == pid:
                    children.append(cpid)
            except Exception:
                continue
        info["children"] = sorted(children)
        return info

    def inspect_process(self, args: Dict[str, Any]) -> ToolResult:
        pid = args.get("pid")
        name = str(args.get("name") or "").strip()
        if pid is None and not name:
            return ToolResult(success=False, error="pid or name is required")
        if pid is not None:
            try:
                pid_int = int(pid)
            except Exception:
                return ToolResult(success=False, error="pid must be an integer")
            info = self._proc_info(pid_int)
            return ToolResult(success=bool(info.get("exists")), content=info, error=None if info.get("exists") else f"Process not found: {pid_int}")
        pids = self._proc_pids_for_name(name)
        processes = [self._proc_info(p) for p in pids]
        return ToolResult(success=True, content={"name": name, "pids": pids, "processes": processes, "count": len(processes)})

    def _signal_name(self, value: str) -> Optional[int]:
        v = (value or "TERM").strip().upper()
        if v.lstrip("-").isdigit():
            return int(v)
        if not v.startswith("SIG"):
            v = "SIG" + v
        sig = getattr(signalmod, v, None)
        return int(sig) if sig is not None else None

    def terminate_process(self, args: Dict[str, Any]) -> ToolResult:
        pid = args.get("pid")
        name = str(args.get("name") or "").strip()
        if pid is None and not name:
            return ToolResult(success=False, error="pid or name is required")
        if not (args.get("approved") or args.get("_approved")):
            return ToolResult(success=False, error="Process termination requires approved=true")
        sig = self._signal_name(str(args.get("signal") or "TERM"))
        if sig is None:
            return ToolResult(success=False, error="Unsupported signal")
        if pid is not None:
            try:
                targets = [int(pid)]
            except Exception:
                return ToolResult(success=False, error="pid must be an integer")
        else:
            targets = self._proc_pids_for_name(name)
            if not targets:
                return ToolResult(success=False, error=f"No processes matched: {name}")
            if not args.get("all_matches") and len(targets) > 1:
                return ToolResult(success=False, error=f"Multiple processes matched '{name}'; pass all_matches=true or use pid")
        allow_critical = bool(args.get("allow_critical", False))
        own_uid = os.getuid()
        results = []
        sent = 0
        for target in sorted(set(targets)):
            record: Dict[str, Any] = {"pid": target}
            pidfd = None
            try:
                if target in (1, os.getpid(), os.getppid()):
                    record.update({"ok": False, "error": "Refusing to terminate critical/current process"})
                else:
                    if hasattr(os, "pidfd_open"):
                        try:
                            pidfd = os.pidfd_open(target)
                        except OSError:
                            pidfd = None
                    info = self._proc_info(target)
                    if not info.get("exists"):
                        record.update({"ok": False, "error": "Process not found"})
                    else:
                        rec_uid = info.get("uid_num")
                        if rec_uid is not None and rec_uid != own_uid:
                            record.update({"ok": False, "error": "Refusing to terminate a process owned by another user"})
                        else:
                            comm = (info.get("comm") or "")
                            if comm in CRITICAL_PROCESS_NAMES and not allow_critical:
                                record.update({"ok": False, "error": f"Refusing to terminate critical process: {comm}"})
                            else:
                                if pidfd is not None:
                                    signalmod.pidfd_send_signal(pidfd, sig)
                                else:
                                    os.kill(target, sig)
                                sent += 1
                                record.update({"ok": True, "signal": int(sig), "comm": comm})
            except Exception as e:
                record.update({"ok": False, "error": str(e)})
            finally:
                if pidfd is not None:
                    try:
                        os.close(pidfd)
                    except Exception:
                        pass
            results.append(record)
        deadline = time.time() + 1.5
        while time.time() < deadline:
            if not any(self._proc_info(r["pid"]).get("state") not in (None, "Z", "X") for r in results if r.get("ok")):
                break
            time.sleep(0.1)
        for record in results:
            if record.get("ok"):
                info = self._proc_info(record["pid"])
                state = info.get("state")
                record["zombie"] = state == "Z"
                record["still_running"] = bool(info.get("exists") and state not in ("Z", "X"))
        return ToolResult(success=sent > 0, content={"targets": results, "sent": sent})

    def launch_application(self, args: Dict[str, Any]) -> ToolResult:
        app_query = str(args.get("app") or "").strip()
        if not app_query:
            return ToolResult(success=False, error="app is required")
        extra = [str(a) for a in (args.get("args") or [])]
        matches = self._match_apps(app_query)
        if matches:
            app = matches[0]
            app_id = str(app.get("id") or "")
            app_id_nostrip = app_id[:-8] if app_id.endswith(".desktop") else app_id
            cmd: Optional[List[str]] = None
            method = None
            try:
                if shutil.which("gtk-launch") and not app.get("terminal"):
                    cmd = ["gtk-launch", app_id_nostrip] + extra
                    method = "gtk-launch"
                elif shutil.which("gio"):
                    cmd = ["gio", "launch", str(app.get("desktop_file"))] + extra
                    method = "gio"
                else:
                    exec_line = _strip_field_codes(app.get("exec") or "")
                    cmd = shlex.split(exec_line) + extra
                    method = "desktop-exec"
                subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
            except Exception as e:
                return ToolResult(success=False, error=f"Failed to launch {app.get('name')}: {e}")
            time.sleep(0.6)
            running = self._app_running(app)
            return ToolResult(success=True, content={
                "launched": True,
                "application": {"name": app.get("name"), "id": app.get("id")},
                "method": method,
                "command": cmd,
                "running_after_launch": running,
            })
        # raw executable / command
        allow_arbitrary = bool(args.get("allow_arbitrary"))
        if not allow_arbitrary:
            return ToolResult(success=False, error="Application not found among installed desktop apps; pass allow_arbitrary=true to launch a raw command")
        if not (args.get("approved") or args.get("_approved")):
            return ToolResult(success=False, error="Launching an arbitrary command requires approved=true")
        try:
            cmd = shlex.split(app_query) + extra
        except Exception as e:
            return ToolResult(success=False, error=f"Invalid command: {e}")
        if not cmd:
            return ToolResult(success=False, error="app is empty")
        program = shutil.which(cmd[0])
        if not program:
            return ToolResult(success=False, error=f"Executable not found: {cmd[0]}")
        try:
            proc = subprocess.Popen([program] + cmd[1:], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
        except Exception as e:
            return ToolResult(success=False, error=f"Failed to launch command: {e}")
        time.sleep(0.4)
        return ToolResult(success=True, content={
            "launched": True,
            "application": None,
            "method": "direct-exec",
            "command": [program] + cmd[1:],
            "pid": proc.pid,
            "running_after_launch": {"running": proc.poll() is None, "pids": [proc.pid]},
        })

    # ---- open / notify ----
    def _xdg_open(self, target: str) -> ToolResult:
        opener = shutil.which("xdg-open") or shutil.which("gio")
        if not opener:
            return ToolResult(success=False, error="No opener available (xdg-open/gio not found)")
        try:
            cmd = [opener, target] if opener.endswith("xdg-open") else [opener, "open", target]
            subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return ToolResult(success=True, content={"target": target, "opened": True, "opener": os.path.basename(opener)})
        except Exception as e:
            return ToolResult(success=False, error=str(e))

    def open_path(self, args: Dict[str, Any]) -> ToolResult:
        path = str(args.get("path", "")).strip()
        if not path:
            return ToolResult(success=False, error="path is required")
        return self._xdg_open(path)

    def open_uri(self, args: Dict[str, Any]) -> ToolResult:
        uri = str(args.get("uri", "")).strip()
        if not uri:
            return ToolResult(success=False, error="uri is required")
        return self._xdg_open(uri)

    def notify(self, args: Dict[str, Any]) -> ToolResult:
        title = str(args.get("title", "")).strip()
        body = str(args.get("body", "")).strip()
        urgency = str(args.get("urgency", "normal")).strip()
        if not title:
            return ToolResult(success=False, error="title is required")
        tool = shutil.which("notify-send")
        if not tool:
            return ToolResult(success=False, error="notify-send not available")
        cmd = [tool]
        if urgency in ("low", "normal", "critical"):
            cmd += ["-u", urgency]
        cmd.append(title)
        if body:
            cmd.append(body)
        try:
            proc = _run(cmd, timeout=10)
            if proc.returncode != 0:
                return ToolResult(success=False, error=proc.stderr.strip() or "notify-send failed")
            return ToolResult(success=True, content={"sent": True, "title": title})
        except Exception as e:
            return ToolResult(success=False, error=str(e))

    # ---- GNOME / D-Bus integration ----
    def dbus_list_names(self, args: Dict[str, Any]) -> ToolResult:
        if not shutil.which("gdbus"):
            return ToolResult(success=False, error="gdbus not available")
        filt = str(args.get("filter", "")).strip().lower()
        limit = max(1, min(int(args.get("limit", 200)), 500))
        try:
            proc = _run(["gdbus", "call", "--session", "--dest", "org.freedesktop.DBus", "--object-path", "/org/freedesktop/DBus", "--method", "org.freedesktop.DBus.ListNames"], timeout=8)
            if proc.returncode != 0:
                return ToolResult(success=False, error=proc.stderr.strip() or "gdbus ListNames failed")
            names = []
            for line in proc.stdout.replace("(", "").replace(")", "").split(","):
                name = line.strip().strip("'")
                if not name:
                    continue
                if not filt or filt in name.lower():
                    names.append(name)
                if len(names) >= limit:
                    break
            return ToolResult(success=True, content={"names": names, "count": len(names), "filter": filt or None})
        except Exception as e:
            return ToolResult(success=False, error=str(e))

    def dbus_introspect(self, args: Dict[str, Any]) -> ToolResult:
        if not shutil.which("gdbus"):
            return ToolResult(success=False, error="gdbus not available")
        destination = str(args.get("destination", "")).strip()
        object_path = str(args.get("object_path", "/org/freedesktop/DBus")).strip()
        if not destination:
            return ToolResult(success=False, error="destination is required")
        try:
            proc = _run(["gdbus", "introspect", "--session", "--dest", destination, "--object-path", object_path], timeout=10)
            if proc.returncode != 0:
                return ToolResult(success=False, error=proc.stderr.strip() or "gdbus introspect failed")
            return ToolResult(success=True, content={"destination": destination, "object_path": object_path, "introspection": proc.stdout[:8000]})
        except Exception as e:
            return ToolResult(success=False, error=str(e))

    def gio_info(self, args: Dict[str, Any]) -> ToolResult:
        if not shutil.which("gio"):
            return ToolResult(success=False, error="gio not available")
        path = str(args.get("path", "")).strip()
        if not path:
            return ToolResult(success=False, error="path is required")
        attributes = str(args.get("attributes", "")).strip()
        cmd = ["gio", "info"]
        if attributes:
            cmd += ["-a", attributes]
        cmd.append(path)
        try:
            proc = _run(cmd, timeout=10)
            if proc.returncode != 0:
                return ToolResult(success=False, error=proc.stderr.strip() or "gio info failed")
            return ToolResult(success=True, content={"path": path, "info": proc.stdout[:8000]})
        except Exception as e:
            return ToolResult(success=False, error=str(e))

    def gnome_session_info(self, args: Dict[str, Any]) -> ToolResult:
        info: Dict[str, Any] = {
            "desktop": os.getenv("XDG_CURRENT_DESKTOP"),
            "session_type": os.getenv("XDG_SESSION_TYPE"),
            "session_desktop": os.getenv("DESKTOP_SESSION"),
            "wayland_display": os.getenv("WAYLAND_DISPLAY"),
            "display": os.getenv("DISPLAY"),
        }
        if shutil.which("gdbus"):
            try:
                p = _run(["gdbus", "call", "--session", "--dest", "org.gnome.SessionManager", "--object-path", "/org/gnome/SessionManager", "--method", "org.gnome.SessionManager.IsSessionRunning"], timeout=5)
                if p.returncode == 0:
                    info["session_running"] = "true" in p.stdout.lower()
                p2 = _run(["gdbus", "call", "--session", "--dest", "org.gnome.SessionManager", "--object-path", "/org/gnome/SessionManager", "--method", "org.freedesktop.DBus.Properties.Get", "org.gnome.SessionManager", "SessionName"], timeout=5)
                if p2.returncode == 0:
                    info["session_name"] = p2.stdout.strip().strip("()'")
                p3 = _run(["gdbus", "call", "--session", "--dest", "org.gnome.SessionManager", "--object-path", "/org/gnome/SessionManager", "--method", "org.freedesktop.DBus.Properties.Get", "org.gnome.SessionManager", "SessionIsActive"], timeout=5)
                if p3.returncode == 0:
                    info["session_active"] = "true" in p3.stdout.lower()
            except Exception:
                pass
        if shutil.which("gsettings"):
            try:
                p = _run(["gsettings", "get", "org.gnome.desktop.interface", "gtk-theme"], timeout=5)
                if p.returncode == 0:
                    info["gtk_theme"] = p.stdout.strip().strip("'")
                p = _run(["gsettings", "get", "org.gnome.desktop.interface", "icon-theme"], timeout=5)
                if p.returncode == 0:
                    info["icon_theme"] = p.stdout.strip().strip("'")
            except Exception:
                pass
        return ToolResult(success=True, content=info)

    # ---- audio ----
    def audio_get(self, args: Dict[str, Any]) -> ToolResult:
        tool = shutil.which("pactl")
        if not tool:
            return ToolResult(success=False, error="pactl not available")
        try:
            vol = _run([tool, "get-sink-volume", "@DEFAULT_SINK@"], timeout=5)
            mute = _run([tool, "get-sink-mute", "@DEFAULT_SINK@"], timeout=5)
            if vol.returncode != 0:
                return ToolResult(success=False, error=vol.stderr.strip() or "failed to get volume")
            return ToolResult(success=True, content={"volume": vol.stdout.strip(), "mute": mute.stdout.strip() if mute.returncode == 0 else None})
        except Exception as e:
            return ToolResult(success=False, error=str(e))

    def audio_set_volume(self, args: Dict[str, Any]) -> ToolResult:
        tool = shutil.which("pactl")
        if not tool:
            return ToolResult(success=False, error="pactl not available")
        volume = str(args.get("volume", "")).strip()
        if not volume:
            return ToolResult(success=False, error="volume is required (e.g. 50%, +5%, -5%)")
        try:
            proc = _run([tool, "set-sink-volume", "@DEFAULT_SINK@", volume], timeout=5)
            if proc.returncode != 0:
                return ToolResult(success=False, error=proc.stderr.strip() or "failed to set volume")
            cur = _run([tool, "get-sink-volume", "@DEFAULT_SINK@"], timeout=5)
            return ToolResult(success=True, content={"set": volume, "volume": cur.stdout.strip() if cur.returncode == 0 else None})
        except Exception as e:
            return ToolResult(success=False, error=str(e))

    def audio_set_mute(self, args: Dict[str, Any]) -> ToolResult:
        tool = shutil.which("pactl")
        if not tool:
            return ToolResult(success=False, error="pactl not available")
        m = args.get("mute")
        if isinstance(m, bool):
            val = "1" if m else "0"
        else:
            val = str(m).strip().lower()
            if val in ("toggle",):
                val = "toggle"
            elif val in ("1", "true", "yes", "on", "mute", "muted"):
                val = "1"
            elif val in ("0", "false", "no", "off", "unmute", "unmuted"):
                val = "0"
            else:
                return ToolResult(success=False, error="mute must be boolean or one of 1/0/toggle")
        try:
            proc = _run([tool, "set-sink-mute", "@DEFAULT_SINK@", val], timeout=5)
            if proc.returncode != 0:
                return ToolResult(success=False, error=proc.stderr.strip() or "failed to set mute")
            cur = _run([tool, "get-sink-mute", "@DEFAULT_SINK@"], timeout=5)
            return ToolResult(success=True, content={"set": val, "mute": cur.stdout.strip() if cur.returncode == 0 else None})
        except Exception as e:
            return ToolResult(success=False, error=str(e))

    # ---- brightness ----
    def brightness_get(self, args: Dict[str, Any]) -> ToolResult:
        tool = shutil.which("brightnessctl")
        if not tool:
            return ToolResult(success=False, error="brightnessctl not available")
        try:
            proc = _run([tool, "-m"], timeout=5)
            if proc.returncode != 0:
                return ToolResult(success=False, error=proc.stderr.strip() or "failed to get brightness")
            raw = proc.stdout.strip()
            parts = raw.split(",") if raw else []
            info = {"raw": raw}
            if len(parts) >= 5:
                info.update({"device": parts[0], "class": parts[1], "current": parts[2], "percent": parts[3], "max": parts[4]})
            return ToolResult(success=True, content=info)
        except Exception as e:
            return ToolResult(success=False, error=str(e))

    def brightness_set(self, args: Dict[str, Any]) -> ToolResult:
        tool = shutil.which("brightnessctl")
        if not tool:
            return ToolResult(success=False, error="brightnessctl not available")
        value = str(args.get("value", "")).strip()
        if not value:
            return ToolResult(success=False, error="value is required (e.g. 50%, +10%, 200)")
        try:
            proc = _run([tool, "set", value], timeout=5)
            if proc.returncode != 0:
                return ToolResult(success=False, error=proc.stderr.strip() or "failed to set brightness")
            cur = _run([tool, "-m"], timeout=5)
            return ToolResult(success=True, content={"set": value, "brightness": cur.stdout.strip() if cur.returncode == 0 else None})
        except Exception as e:
            return ToolResult(success=False, error=str(e))

    # ---- media ----
    def media_status(self, args: Dict[str, Any]) -> ToolResult:
        tool = shutil.which("playerctl")
        if not tool:
            return ToolResult(success=False, error="playerctl not available")
        try:
            players = _run([tool, "-l"], timeout=5)
            status = _run([tool, "status"], timeout=5)
            meta = _run([tool, "metadata", "--format", "{{playerName}}|{{status}}|{{title}}|{{artist}}"], timeout=5)
            return ToolResult(success=True, content={
                "players": players.stdout.strip().splitlines() if players.returncode == 0 and players.stdout.strip() else [],
                "status": status.stdout.strip() if status.returncode == 0 else None,
                "metadata": meta.stdout.strip() if meta.returncode == 0 else None,
                "available": players.returncode == 0 and bool(players.stdout.strip()),
            })
        except Exception as e:
            return ToolResult(success=False, error=str(e))

    def media_control(self, args: Dict[str, Any]) -> ToolResult:
        tool = shutil.which("playerctl")
        if not tool:
            return ToolResult(success=False, error="playerctl not available")
        action = str(args.get("action", "")).strip().lower()
        allowed = {"play", "pause", "play-pause", "next", "previous", "stop"}
        if action not in allowed:
            return ToolResult(success=False, error=f"action must be one of {sorted(allowed)}")
        cmd = [tool]
        player = str(args.get("player", "")).strip()
        if player:
            cmd += ["-p", player]
        cmd.append(action)
        try:
            proc = _run(cmd, timeout=5)
            if proc.returncode != 0:
                return ToolResult(success=False, error=proc.stderr.strip() or "playerctl command failed")
            status = _run([tool, "status"], timeout=5)
            return ToolResult(success=True, content={"action": action, "status": status.stdout.strip() if status.returncode == 0 else None})
        except Exception as e:
            return ToolResult(success=False, error=str(e))

    # ---- clipboard ----
    def clipboard_get(self, args: Dict[str, Any]) -> ToolResult:
        if shutil.which("wl-paste"):
            try:
                proc = _run(["wl-paste", "--no-newline"], timeout=5)
                if proc.returncode != 0:
                    return ToolResult(success=True, content={"text": "", "available": True, "note": proc.stderr.strip() or "no text"})
                return ToolResult(success=True, content={"text": proc.stdout, "available": True})
            except Exception as e:
                return ToolResult(success=False, error=str(e))
        return ToolResult(success=False, error="No supported clipboard read tool available (wl-paste/xclip/xsel)")

    def clipboard_set(self, args: Dict[str, Any]) -> ToolResult:
        text = str(args.get("text", ""))
        if shutil.which("wl-copy"):
            try:
                proc = _run(["wl-copy"], timeout=5, input_text=text)
                if proc.returncode != 0:
                    return ToolResult(success=False, error=proc.stderr.strip() or "wl-copy failed")
                return ToolResult(success=True, content={"set": True, "length": len(text)})
            except Exception as e:
                return ToolResult(success=False, error=str(e))
        return ToolResult(success=False, error="No supported clipboard write tool available (wl-copy/xclip/xsel)")

    # ---- restricted UI automation ----
    def screenshot(self, args: Dict[str, Any]) -> ToolResult:
        path = str(args.get("path") or os.path.join(tempfile.gettempdir(), f"nexus_screenshot_{int(time.time())}.png"))
        if shutil.which("grim"):
            try:
                proc = _run(["grim", path], timeout=10)
                if proc.returncode == 0 and os.path.exists(path):
                    return ToolResult(success=True, content={"path": path, "captured": True, "exists": True})
                return ToolResult(success=False, error=(proc.stderr.strip() or "Screenshot not supported by current compositor/session"), content={"path": path, "captured": False})
            except Exception as e:
                return ToolResult(success=False, error=str(e))
        return ToolResult(success=False, error="No screenshot backend available (grim/portal not configured)")

    def input_text(self, args: Dict[str, Any]) -> ToolResult:
        text = str(args.get("text", ""))
        if not text:
            return ToolResult(success=False, error="text is required")
        if shutil.which("wtype"):
            try:
                proc = _run(["wtype", text], timeout=10)
                if proc.returncode == 0:
                    return ToolResult(success=True, content={"typed": True, "length": len(text)})
                return ToolResult(success=False, error=(proc.stderr.strip() or "Virtual keyboard input not supported by current compositor"))
            except Exception as e:
                return ToolResult(success=False, error=str(e))
        return ToolResult(success=False, error="No supported input backend available (wtype/ydotool) or compositor does not allow virtual input")


def _exec_program(exec_line: str) -> str:
    try:
        parts = shlex.split(_strip_field_codes(exec_line or ""))
    except Exception:
        parts = []
    if not parts:
        return ""
    if parts[0] in ("env",) and len(parts) > 1:
        # skip env assignments
        for p in parts[1:]:
            if "=" not in p:
                return p
        return ""
    return parts[0]


def _strip_field_codes(exec_line: str) -> str:
    # remove desktop entry field codes (%f %F %u %U %i %c %k) and common placeholders
    return " ".join(t for t in (exec_line or "").split() if not (len(t) >= 2 and t.startswith("%")))


_ATSPI_CACHE: Dict[str, Any] = {"at": 0.0, "data": None}
_ATSPI_CACHE_TTL = 2.0


def _atspi_windows(force: bool = False) -> Dict[str, Any]:
    now = time.time()
    cached = _ATSPI_CACHE.get("data")
    if not force and cached is not None and (now - float(_ATSPI_CACHE.get("at") or 0)) < _ATSPI_CACHE_TTL:
        return cached
    py = shutil.which("python3")
    if not py:
        data = {"available": False, "error": "python3 not available for AT-SPI helper"}
    else:
        try:
            proc = _run([py, "-c", ATSPI_WINDOWS_SCRIPT], timeout=15)
            if proc.returncode != 0:
                data = {"available": False, "error": (proc.stderr.strip() or "AT-SPI helper failed")[:500]}
            else:
                parsed = json.loads(proc.stdout.strip() or "{}")
                data = parsed if isinstance(parsed, dict) else {"available": False, "error": "AT-SPI returned invalid data"}
        except Exception as e:
            data = {"available": False, "error": str(e)}
    _ATSPI_CACHE["data"] = data
    _ATSPI_CACHE["at"] = now
    return data
