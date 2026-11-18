# PHASE 1 — Create the desktop application foundation

## Objective

Build an actual installable desktop application with a functioning frontend and backend connection.

### Step 1.1 — Initialize Tauri

1. Create a new Tauri project.
2. Configure React and TypeScript.
3. Configure the application identifier.
4. Configure the application name and window properties.
5. Configure development and production commands.
6. Configure the initial application permissions.
7. Verify that Tauri launches successfully on GNOME Wayland.

### Step 1.2 — Create the frontend project structure

Establish separate directories for:

- Application shell.
- Navigation.
- Dashboard.
- Chat.
- Coding agent.
- Computer agent.
- Companion.
- Tasks.
- Memory.
- MCP management.
- Models.
- Integrations.
- Settings.
- Shared components.
- API clients.
- State management.
- Styling.
- Type definitions.

### Step 1.3 — Create the application design system

Implement:

1. Color variables.
2. Typography.
3. Spacing system.
4. Border and radius system.
5. Button variants.
6. Input components.
7. Dropdown menus.
8. Modal dialogs.
9. Tooltips.
10. Notification components.
11. Loading indicators including thinking and working state styling for autonomous actions.
12. Empty states.
13. Error states.
14. Confirmation dialogs.
15. Reusable cards and panels.

Use the companion chat visual direction as the primary desktop reference: restrained dark blue-gray surfaces, soft lavender accents, readable message contrast, and a clear distinction between navigation, companion presence, conversation, and optional context. See `docs/chat-experience.md` and `docs/nexus-ai-chat-preview.svg`.

Support dark and light themes. Theme changes must preserve contrast and hierarchy; do not make color the only indicator of agent or connection state.

### Step 1.4 — Implement the main application shell

Build:

- Sidebar.
- Top navigation.
- Main content area.
- Optional, collapsible context panel.
- Status bar.
- Window controls.
- Global search.
- Notification centre.
- User settings access.

Implement collapsible navigation and resizable workspace panels. The chat and companion workspace must be able to present a dedicated companion stage beside the central conversation, with the context panel independently collapsible. Keep the conversation and composer usable as the window narrows.

### Step 1.5 — Build the initial screens

Create all major navigation destinations.

At this stage, screens may use clearly labelled demonstration data, but all controls must be connected to a defined interaction or service contract.

Do not implement fake AI execution.

### Step 1.6 — Build the backend foundation

1. Create the Python backend.
2. Create the FastAPI application.
3. Configure Pydantic settings.
4. Create API routers.
5. Configure CORS for development.
6. Configure structured logging.
7. Add health-check endpoints.
8. Add application version endpoint.
9. Add exception handlers.
10. Add API documentation.

### Step 1.7 — Connect frontend and backend

1. Create a centralized API client.
2. Configure request handling.
3. Configure response handling.
4. Implement error notifications.
5. Implement loading states.
6. Configure WebSocket communication.
7. Implement connection monitoring.
8. Test frontend/backend communication.

### Step 1.8 — First application verification

Verify:

- The desktop application launches.
- Navigation works.
- Theme switching works.
- Settings open correctly.
- The backend starts.
- The frontend can reach the backend.
- WebSocket connections work.
- Backend failures are displayed appropriately.

**Completion criteria:** NEXUS AI exists as a working desktop application, even though it does not yet possess autonomous intelligence.

---


**Roadmap:** [Index](../../overview) · [← Phase 0: Project planning, requirements and technical preparation](phase-00.md) · [Phase 2: Implement the complete frontend →](phase-02.md)
