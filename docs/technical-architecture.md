# NEXUS AI — Technical Architecture

**Status:** Draft — Phase 0, Steps 0.2–0.9  
**Source:** NEXUS_AI_Revised_Master_Roadmap.md, PART II — ARCHITECTURE AND TECHNICAL DECISIONS

## 1. Architecture style

Modular monolith with clear module boundaries. Components can be separated later if scale or reliability requires it. Not a distributed microservice system.

## 2. Layer overview

### 2.1 Desktop layer (Tauri + React + TypeScript + Tailwind CSS)

- Installable desktop shell.
- React/TypeScript UI with Tailwind CSS styling.
- Tauri commands and events for carefully scoped desktop integration.
- Frontend communicates with backend through a documented API.
- The primary companion/chat workspace composes a navigation rail, a dedicated companion stage, a central conversation, and a collapsible context panel. Its visual and responsive behavior is specified in [chat-experience.md](./chat-experience.md).
- The context panel displays approved, user-facing activity summaries and persisted memory records; it is not a surface for private model reasoning or credentials.

### 2.2 Backend layer (Python + FastAPI + Pydantic)

- Python hosts application services.
- FastAPI exposes the local application API.
- Pydantic validates requests and structured data.
- WebSockets stream agent events, progress and live responses.
- Background worker/scheduler handles long-running and scheduled work.
- Persistent execution engine records progress independently of model context.

The backend runs as a managed child process or local service controlled by the desktop application. Startup, readiness checks, shutdown, restart and crash-recovery behaviour are defined explicitly.

### 2.3 Data layer

Starting point:
- SQLite for local application data and initial single-user deployment.
- Migration layer (Alembic or equivalent).
- Repository/data-access layer preventing business logic from depending directly on SQLite-specific SQL.
- Local filesystem storage for large attachments, logs and model files.
- Optional PostgreSQL for concurrent/remote/larger-scale deployments.
- Optional vector search when semantic retrieval has a tested need (not a prerequisite for first release).

### 2.4 AI model layer

Provider-independent model interface with local and cloud adapters.

Common model interface covers:
- Text generation and streaming.
- Structured output.
- Tool-call requests.
- Context-window metadata.
- Token usage where available.
- Cancellation.
- Timeouts and retries.
- Provider errors.
- Model capability declarations.

Possible local inference: llama.cpp. Cloud providers added through individual adapters. Never hard-code the whole application to one model vendor.

### 2.5 Automation layer

Best available interface per operation:
- Native Linux APIs and D-Bus/GIO for system integration.
- AT-SPI2 for Linux accessibility where supported.
- xdg-desktop-portal interfaces for permission-mediated Wayland screen capture and remote input.
- Playwright for browser automation.
- LibreOffice UNO for supported LibreOffice automation.
- Windows UI Automation and COM/VBA for Windows-specific applications.
- OCR and OpenCV for visual fallback workflows.

Do not assume X11 techniques work unchanged on GNOME Wayland.

### 2.6 MCP layer

MCP is an integration protocol, not the entire internal execution architecture.
- Native backend services for core internal operations.
- Expose selected capabilities through MCP when reusable by agents or external clients.
- Support stdio and remote Streamable HTTP transports.
- Every external MCP server is a separate trust boundary; inspect configuration, tools, permissions and outputs before allowing agent use.

## 3. Four agents

| Agent | Responsibility |
|---|---|
| Personal Conversational Companion | Natural conversation, emotional awareness, memory, follow-ups, proactive engagement, conversation-to-action classification, handoff to other agents |
| Autonomous Coding Agent | Project-aware software engineering: inspect, edit, run, test, debug, Git, verify |
| Autonomous Computer Agent | OS and desktop application operation: files, apps, windows, processes, browser, GUI automation |
| Life Management Agent | Personal organization: tasks, reminders, schedules, deadlines, goals, summaries |

All four are coordinated by one central orchestrator.

## 4. Orchestrator responsibilities

1. Receive the user's message or action.
2. Determine intent and risk level.
3. Identify the appropriate agent or agents.
4. Provide only the context and permissions those agents need.
5. Track delegated work.
6. Coordinate dependencies and shared resources.
7. Collect verified results.
8. Return a clear response through the companion or relevant workspace.

## 5. Shared services

- Model management (provider routing, selection, capabilities).
- Memory management (working, long-term, semantic, episodic; user controls).
- Tool execution (registry, validation, permission checks, verification, audit).
- MCP management (server connections, tool discovery, isolation, health).
- Task management (TODOs, dependencies, execution state, checkpoints).
- Permission management (categories, agent/tool/resource/session scoping, approvals).
- Scheduling (reminders, recurring activities, background worker).
- Notifications (desktop notifications, quiet hours).
- Logging and observability (events, execution records, audit trails).
- Database and persistence (repositories, migrations, backup/restore).

## 6. Permission categories

| Permission | Example |
|---|---|
| Read | Read an authorized document |
| Write | Create a new document |
| Modify | Edit an existing project file |
| Delete | Delete a file |
| Execute | Run a command |
| Install | Install software |
| Network | Access an external website |
| Credentials | Use a stored credential |
| Financial | Make a purchase or payment |
| Administrative | Perform privileged system operations |

Permissions defined by agent, tool, resource and session. Least privilege. Destructive, privileged, financial, credential-sensitive or externally consequential operations require confirmation. Authorization decisions logged.

## 7. Module structure (suggested)

```
nexus-ai/
├── desktop/
│   ├── src-tauri/
│   └── src/
│       ├── app/
│       ├── components/
│       ├── pages/
│       ├── features/
│       │   ├── chat/
│       │   ├── companion/
│       │   ├── coding/
│       │   ├── computer/
│       │   ├── life-management/
│       │   ├── tasks/
│       │   ├── memory/
│       │   ├── mcp/
│       │   ├── models/
│       │   └── settings/
│       ├── services/
│       ├── state/
│       └── styles/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── database/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── services/
│   │   ├── agents/
│   │   │   ├── companion/
│   │   │   ├── coding/
│   │   │   ├── computer/
│   │   │   └── life_management/
│   │   ├── orchestration/
│   │   ├── execution/
│   │   ├── tools/
│   │   ├── mcp/
│   │   ├── memory/
│   │   ├── automation/
│   │   ├── adapters/
│   │   ├── scheduling/
│   │   ├── permissions/
│   │   └── observability/
│   └── tests/
├── mcp-servers/
├── docs/
├── scripts/
├── migrations/
└── README.md
```

Create modules when their phase begins — not every directory on day one.

## 8. API and WebSocket conventions

### REST API
- FastAPI with Pydantic request/response schemas.
- Standard HTTP status codes.
- JSON request/response bodies.
- CORS configured for development (restricted in production).
- Versioned endpoint prefix (e.g. `/api/v1`).

### WebSocket events
Structured events streamed to the frontend for live monitoring:
- `agent.started`, `agent.planning`, `agent.delegated`, `agent.completed`
- `task.created`, `task.started`, `task.completed`, `task.blocked`
- `tool.called`, `tool.failed`, `tool.verified`
- `mcp.connected`, `mcp.disconnected`
- `computer.action_started`, `computer.action_verified`
- `memory.created`
- `conversation.followup_detected`
- `approval.requested`, `approval.granted`, `approval.denied`

Frontend receives relevant events through WebSockets and displays understandable activity summaries.

## 9. Initial database entities

- Users / settings
- Conversations and messages
- Agent executions (execution ID, agent ID, objective, plan, current task, completed/pending tasks, tool calls, results, errors, checkpoints, approvals, final report)
- Tasks and subtasks (with dependencies and status)
- Memories (categories, source references, embeddings optional, retention)
- MCP servers and permissions
- Tool execution records (calls, results, errors, verification)
- Approval records (requested, granted, denied)
- Attachment metadata and filesystem storage references

Database-specific operations behind the data-access layer so PostgreSQL can be introduced later.

## 10. Desktop shell backend lifecycle

The Tauri application manages the Python backend:
- Startup command launches the backend process.
- Readiness health-check endpoint polled until ready.
- Backend connection state displayed in the UI.
- Shutdown command stops the backend cleanly.
- Restart on crash; crash-recovery behaviour documented.
- No unintended background processes left after shutdown.

## 11. Dependencies and platform-specific components

### Development tools (verified independently)
- Git
- Supported Python interpreter (project virtual environment; do not replace system Python)
- Node.js and npm or pnpm
- Rust and Cargo
- Tauri prerequisites
- Code editor
- Browser testing dependencies
- SQLite tooling

### Platform-specific (initial target: Arch Linux, GNOME, Wayland)
- D-Bus / GIO for system integration
- AT-SPI2 for accessibility
- xdg-desktop-portal for screen capture and remote input
- pacman adapter for package management (with approval)
- Playwright for browser automation
- Tesseract for OCR
- OpenCV for image processing
- llama.cpp for local inference (optional first release)

Windows support added later through platform-specific adapters (UI Automation, COM, etc.).

## 12. Cross-cutting requirements

- Persistent execution state: every long-running task persists execution ID, agent ID, objective, plan, current task, completed/pending tasks, tool calls/results, errors, checkpoints, approvals, verification evidence, final report. Reconstruct from storage after crash.
- Event-driven updates: important operations produce events streamed via WebSockets.
- Untrusted content: website content, documents, emails, screenshots, terminal output, downloads and external MCP responses treated as untrusted input.
- Observability: record agent/task status, actions, tool calls/results, duration, errors, retries, model usage, token usage, MCP events, permission decisions, verification outcomes. Do not expose private internal reasoning traces.
- Reliability: every long-running operation has a persistent execution ID; every tool has input validation and timeout; every important side effect has verification; every risky action has approval; every agent can be stopped; every failed task has clear state; every external integration can be disconnected; every stored memory has user controls; every feature has tests and documented limitations.
