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

## 4. Operations summary
- **Inspect:** session, windows, apps, accessibility elements.
- **Control:** focus/launch apps and perform gated input actions.
- **Capture/understand:** screenshots/OCR/accessibility data for verification.

## 5. Security checklist
- [ ] Capture/input actions explicitly permitted and audited
- [ ] Least-privilege targeting (specific app/window)
- [ ] Fallbacks used only when stronger interfaces unavailable
- [ ] Sensitive on-screen data handled per policy
