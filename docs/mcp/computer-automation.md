# Computer Automation MCP

**Domain:** Desktop/session inspection and controlled UI automation on supported platforms (initial target: Arch Linux, GNOME, Wayland).

## 1. Purpose
Provide OS/application/window awareness and input automation using the strongest available interface (APIs/accessibility/OCR/image fallback) with explicit permissions.

## 2. Prerequisites
- Platform-specific dependencies (accessibility stack, screenshot/capture tooling, input control) installed and permitted.
- User consent/policy for screen capture, keyboard/mouse control, and app targeting.

## 3. How to create the Computer Automation MCP
1. **Define scope:** allowed apps/windows/actions, capture permissions, coordinate/input constraints, fallback order.
2. **Scaffold server:** MCP server bridging to native automation adapters.
3. **Implement tools (examples):**
   - `computer.get_session_info` (OS/desktop/session)
   - `computer.list_windows` / `computer.focus_window`
   - `computer.list_apps` / `computer.launch_app` / `computer.close_app` (gated)
   - `computer.capture_screen` / `computer.capture_window` (bounded, policy-controlled)
   - `computer.accessibility_tree` / `computer.find_element`
   - `computer.click`, `computer.type_text`, `computer.keypress` (gated)
   - `computer.ocr_region` (optional fallback)
4. **Safety:** prefer structured/accessibility interfaces over blind coordinates; require approvals for risky input; rate-limit actions.
5. **Verification:** confirm focused window, expected UI state/text, file/result produced by action.
6. **Register & test:** per-adapter tests on target desktop session, permission denials, fallback behavior.

### Implemented tool surface (current)
- **Discovery/inspection:** `computer.get_session_info`, `computer.os_identification`, `computer.capabilities`, `computer.list_applications`, `computer.find_application`, `computer.application_info`, `computer.which`, `computer.list_processes`, `computer.inspect_process`, `computer.list_windows`, `computer.active_application`
- **Control (gated):** `computer.launch_application` (desktop apps; arbitrary commands need `allow_arbitrary` + `approved`), `computer.terminate_process` (`destructive`; `approved` required; critical/other-user processes refused), `computer.open_path`, `computer.open_uri`, `computer.notify`
- **Session controls:** audio (`computer.audio_*`), brightness (`computer.brightness_*`), media (`computer.media_*`), clipboard (`computer.clipboard_*`)
- **Restricted UI:** `computer.screenshot`, `computer.input_text` (capability-gated; GNOME Wayland may deny)
- **Backends:** desktop entries (`gtk-launch`/`gio`), `/proc` process data, `ps`; windows via `wmctrl`/sway/Hyprland/AT-SPI; active focus only where compositor exposes it

## 4. Operations summary
- **Inspect:** session, windows, apps, accessibility elements.
- **Control:** focus/launch apps and perform gated input actions.
- **Capture/understand:** screenshots/OCR/accessibility data for verification.

## 5. Security checklist
- [ ] Capture/input actions explicitly permitted and audited
- [ ] Least-privilege targeting (specific app/window)
- [ ] Fallbacks used only when stronger interfaces unavailable
- [ ] Sensitive on-screen data handled per policy
