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
import re
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.mcp.base import BaseMcpServer, McpServerConfig, ToolDefinition, ToolResult


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
        t(ToolDefinition("computer.list_applications", "List installed desktop applications", {"type": "object", "properties": {"limit": {"type": "integer"}}}, "read"), self.list_applications)
        t(ToolDefinition("computer.list_windows", "List desktop windows if a supported backend is available", {"type": "object", "properties": {}}, "read"), self.list_windows)
        # Open / launch / notify
        t(ToolDefinition("computer.open_path", "Open a file or path with the default handler (xdg-open)", {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}, "execute"), self.open_path)
        t(ToolDefinition("computer.open_uri", "Open a URL or URI with the default handler (xdg-open/gio)", {"type": "object", "properties": {"uri": {"type": "string"}}, "required": ["uri"]}, "execute"), self.open_uri)
        t(ToolDefinition("computer.notify", "Send a desktop notification", {"type": "object", "properties": {"title": {"type": "string"}, "body": {"type": "string"}, "urgency": {"type": "string"}}, "required": ["title"]}, "execute"), self.notify)
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
        caps["process_list"] = {"supported": bool(shutil.which("ps"))}
        caps["list_applications"] = {"supported": True}
        caps["window_control"] = {"supported": False, "reason": "No supported window management backend available in this session"}
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

    def _parse_desktop(self, path: str) -> Optional[Dict[str, str]]:
        try:
            name = exec_cmd = icon = None
            in_entry = False
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    line = line.strip()
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
                    if k == "Name" and name is None:
                        name = v
                    elif k == "Exec" and exec_cmd is None:
                        exec_cmd = v
                    elif k == "Icon" and icon is None:
                        icon = v
            if not name:
                return None
            return {"name": name, "exec": exec_cmd or "", "icon": icon or "", "desktop_file": path, "id": os.path.basename(path)}
        except Exception:
            return None

    def list_applications(self, args: Dict[str, Any]) -> ToolResult:
        limit = int(args.get("limit", 100))
        dirs = ["/usr/share/applications", "/usr/local/share/applications", os.path.expanduser("~/.local/share/applications")]
        seen = set()
        apps: List[Dict[str, str]] = []
        for d in dirs:
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
                apps.append(app)
                if len(apps) >= limit:
                    break
            if len(apps) >= limit:
                break
        return ToolResult(success=True, content={"applications": apps, "count": len(apps)})

    def list_windows(self, args: Dict[str, Any]) -> ToolResult:
        return ToolResult(success=False, error="Window listing/control not supported by available backend in this session", content={"windows": [], "session": self._session(), "supported": False})

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
