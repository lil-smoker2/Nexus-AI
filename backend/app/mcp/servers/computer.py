"""Computer Automation MCP server: OS/session control primitives.

Works on Arch Linux; on GNOME Wayland some UI automation (global input injection,
arbitrary screen capture, window enumeration/control) is restricted by the compositor
and available permissions/tools. Supported controls (open/launch, notifications,
audio, brightness, media, clipboard, app/process/session inspection) are exposed
with capability reporting.
"""

from __future__ import annotations

import glob
import os
import platform
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.mcp.base import BaseMcpServer, McpServerConfig, ToolDefinition, ToolResult


def _run(cmd: List[str], timeout: int = 10, input_text: Optional[str] = None) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, input=input_text)


class ComputerAutomationMcpServer(BaseMcpServer):
    server_type = "computer"

    def __init__(self, config: McpServerConfig):
        super().__init__(config)
        self._register_tools()

    def _register_tools(self) -> None:
        t = self.register_tool
        # Info / discovery
        t(ToolDefinition("computer.get_session_info", "Get OS and session info", {"type": "object", "properties": {}}, "read"), self.get_session_info)
        t(ToolDefinition("computer.capabilities", "Report supported OS-control capabilities and Wayland/compositor limitations", {"type": "object", "properties": {}}, "read"), self.capabilities)
        t(ToolDefinition("computer.list_processes", "List running processes (top)", {"type": "object", "properties": {"limit": {"type": "integer"}}}, "read"), self.list_processes)
        t(ToolDefinition("computer.which", "Locate an executable", {"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]}, "read"), self.which)
        t(ToolDefinition("computer.list_applications", "List installed desktop applications", {"type": "object", "properties": {"limit": {"type": "integer"}}}, "read"), self.list_applications)
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
        # UI automation (may be restricted on Wayland)
        t(ToolDefinition("computer.screenshot", "Capture a screenshot to a file if compositor/permissions allow", {"type": "object", "properties": {"path": {"type": "string"}}, "required": []}, "execute"), self.screenshot)
        t(ToolDefinition("computer.input_text", "Type text via virtual keyboard if supported by compositor", {"type": "object", "properties": {"text": {"type": "string"}}, "required": ["text"]}, "execute"), self.input_text)
        t(ToolDefinition("computer.list_windows", "List desktop windows if a supported backend is available", {"type": "object", "properties": {}}, "read"), self.list_windows)

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
        return ToolResult(success=True, content=info)

    def capabilities(self, args: Dict[str, Any]) -> ToolResult:
        sess = self._session()
        caps: Dict[str, Any] = {}
        caps["open_uri"] = {"supported": bool(shutil.which("xdg-open") or shutil.which("gio"))}
        caps["notify"] = {"supported": bool(shutil.which("notify-send"))}
        caps["audio"] = {"supported": bool(shutil.which("pactl"))}
        caps["brightness"] = {"supported": bool(shutil.which("brightnessctl"))}
        caps["media"] = {"supported": bool(shutil.which("playerctl"))}
        caps["clipboard"] = {"supported": bool(shutil.which("wl-copy") and shutil.which("wl-paste")) if sess.get("session_type") == "wayland" else bool((shutil.which("wl-copy") and shutil.which("wl-paste")) or shutil.which("xclip") or shutil.which("xsel"))}
        caps["process_list"] = {"supported": bool(shutil.which("ps"))}
        caps["list_applications"] = {"supported": True}
        # restricted on GNOME Wayland without extra perms/backends
        caps["screenshot"] = {"supported": False, "reason": "Wayland compositor/portal screen capture not available non-interactively in this session (grim/portal restricted)"}
        caps["input_injection"] = {"supported": False, "reason": "Compositor virtual keyboard/pointer protocols not exposed (wtype/ydotool unavailable or unsupported)"}
        caps["window_control"] = {"supported": False, "reason": "GNOME Shell window introspection/control APIs restricted (Shell.Eval disabled) and no Wayland window-management backend available"}
        notes = []
        if sess.get("session_type") == "wayland":
            notes.append("Running on Wayland: global screenshot/input/window control is compositor-restricted; use supported controls (open/notify/audio/brightness/media/clipboard/apps) or configure portal/AT-SPI/input backends for deeper automation.")
        return ToolResult(success=True, content={"session": sess, "capabilities": caps, "notes": notes, "works_on_arch_linux": True})

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
            # machine format: device,class,current,percent,max
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
                    # empty clipboard or no offer can be non-zero sometimes; return empty-ish
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
        # grim only works if compositor supports screencopy protocol
        if shutil.which("grim"):
            try:
                proc = _run(["grim", path], timeout=10)
                if proc.returncode == 0 and os.path.exists(path):
                    return ToolResult(success=True, content={"path": path, "captured": True})
                return ToolResult(success=False, error=(proc.stderr.strip() or "Screenshot not supported by current Wayland compositor/session"), content={"path": path})
            except Exception as e:
                return ToolResult(success=False, error=str(e))
        return ToolResult(success=False, error="No screenshot tool available (grim/portal)")

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
        return ToolResult(success=False, error="No supported input tool available (wtype/ydotool) or compositor does not allow virtual input")

    def list_windows(self, args: Dict[str, Any]) -> ToolResult:
        # No reliable Wayland window listing backend available in this environment
        return ToolResult(success=False, error="Window listing/control not supported in this session (GNOME Wayland restricts window introspection; no wmctrl/Shell API backend available)", content={"windows": [], "session": self._session()})
