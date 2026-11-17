# Browser MCP

**Domain:** Browser session control, navigation, page inspection, and safe web interaction.

## 1. Purpose
Provide structured browser automation (DOM/accessibility-first) for research, downloads, and web workflows.

## 2. Prerequisites
- Browser runtime/driver (e.g. Playwright/CDP) installed and permitted.
- Download directory policy and network/domain constraints.

## 3. How to create the Browser MCP
1. **Define scope:** allowed domains/actions, download paths, headless/headed mode, session limits.
2. **Scaffold server:** MCP server exposing browser lifecycle and interaction tools.
3. **Implement tools:**
   - `browser.create_session` / `browser.close_session`
   - `browser.navigate` (`url`)
   - `browser.get_page_info` / `browser.snapshot` (DOM/accessibility/text)
   - `browser.click`, `browser.type`, `browser.select`, `browser.submit`
   - `browser.wait_for` (selector/text/state)
   - `browser.download` (to allowed path, report result)
   - `browser.screenshot` (optional, bounded)
4. **Safety:** domain allow/deny, block credential entry to untrusted targets per policy, treat page content as untrusted.
5. **Verification:** confirm navigation target, element state changes, download file exists.
6. **Register & test:** handshake/discovery, navigation/forms/downloads, timeout and error handling.

## 4. Operations summary
- **Session:** open/close managed browser contexts.
- **Navigate & inspect:** URLs, DOM/accessibility snapshots, text extraction.
- **Interact:** click/type/select/submit with waits.
- **Capture:** downloads/screenshots to approved locations.

## 5. Security checklist
- [ ] Domain and action restrictions enforced
- [ ] Downloads confined to allowed paths
- [ ] Untrusted page content not treated as instructions
- [ ] Sessions audited and cleaned up
