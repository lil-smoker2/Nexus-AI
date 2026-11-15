# NEXUS AI — Revised Master Product Specification and Development Roadmap

**Document purpose:** A practical, implementation-oriented specification for designing, building, testing, and releasing NEXUS AI.

**Product type:** Standalone, autonomous, multi-agent desktop AI environment  
**Initial platform:** Arch Linux, GNOME, Wayland  
**Future platform support:** Windows and other Linux desktop environments through platform-specific adapters  
**Desktop shell:** Tauri  
**Frontend:** React, TypeScript, Tailwind CSS  
**Backend:** Python, FastAPI, Pydantic  
**Initial persistence:** SQLite; PostgreSQL and vector-search support can be added when justified  
**AI providers:** Local and cloud language models through a provider-independent interface  
**Automation:** Native operating-system APIs, accessibility interfaces, browser automation, application adapters, OCR and computer vision  
**External tool integration:** Model Context Protocol (MCP)  
**Development approach:** Modular, incremental, test-driven, security-first

---

# PART I — PRODUCT VISION

## 1. What NEXUS AI is

NEXUS AI is a standalone desktop application that acts as a personal AI operating environment. It combines a natural conversational companion with specialized agents that can plan and carry out work on the user's computer.

It is not merely a chatbot, a code editor extension, a collection of scripts, or a web application opened in a browser. The user should be able to launch one desktop application and access its conversational, coding, computer-control, and personal-organization capabilities from a unified interface.

The system should be able to understand a request, determine what kind of work is required, create a plan, select the appropriate agent, use authorized tools, monitor progress, recover from interruptions, verify results, and explain what it accomplished.

## 2. The four specialized agents

### 2.1 Personal Conversational Companion

The companion is the user's natural point of contact with NEXUS AI. It must support both ordinary conversation and actionable requests.

It should respond naturally to everyday expressions, including short messages:

- User: "Hey."
- Companion: "Hey! How are you doing?"
- User: "Good morning."
- Companion: "Good morning! How did you sleep?"
- User: "I'm bored."
- Companion: "Want to find something interesting to do?"
- User: "I had a difficult day."
- Companion: "I'm sorry it was a difficult one. Do you want to talk about what happened?"
- User: "I missed you."
- Companion: "It's lovely to hear from you again."

Responses should be brief when the conversation calls for brevity, varied rather than rigid templates, and informed by the current conversation. The companion should be warm and supportive without pretending to be a human being or claiming to experience human emotions.

Core capabilities:

- Natural greetings, casual chat, humour, goodbyes and topic changes.
- Conversation history and context reconstruction.
- Working, long-term, semantic and episodic memory.
- Personal profile containing user-approved preferences, interests and goals.
- Detection of questions that were not answered and topics awaiting an update.
- Tracking of promises, plans, decisions and unfinished discussions.
- Relevant follow-up questions at appropriate times.
- Recognition of conversational signals such as frustration, excitement, sadness, confusion or boredom, with suitable tone adjustment.
- User-controlled proactive conversations, quiet hours and frequency limits.
- Memory inspection, correction, deletion and retention controls.
- Handoff of actionable requests to the coding, computer or life-management agent.
- Clear reporting of what delegated agents actually completed.

The companion must not treat every sentence as a command. It should distinguish casual conversation from a request, a goal, a reminder, a progress update or a potential task.

### 2.2 Autonomous Coding Agent

The coding agent is a project-aware software engineering agent, comparable in purpose to autonomous coding tools such as Kilo Code.

It should be able to:

- Open and inspect a selected project workspace.
- Understand project structure, languages, frameworks and dependencies.
- Search files and symbols.
- Read and edit code.
- Create, move, rename and delete files subject to permissions.
- Produce a plan and persistent TODO list.
- Run terminal commands in a controlled environment.
- Install project dependencies when authorized.
- Run tests, builds, linters and formatters.
- Interpret errors and stack traces.
- Debug and revise its changes.
- Inspect Git status and diffs.
- Preserve project-specific memory and decisions.
- Resume interrupted work.
- Verify the result and provide a change report.

It must not silently overwrite important user work. Changes should be reviewable, and risky operations should require approval.

### 2.3 Autonomous Computer Agent

The computer agent operates the user's computer and supported desktop applications.

It should be able to:

- Inspect operating-system and desktop-session information.
- Find, read, create, copy, move and organize files.
- Launch and manage applications.
- Inspect windows and processes.
- Navigate websites and interact with browser pages.
- Work inside supported desktop applications.
- Use application APIs where available.
- Use accessibility interfaces to identify controls.
- Use OCR and image matching when stronger interfaces are unavailable.
- Perform controlled keyboard and mouse actions where necessary.
- Verify the result of important actions.
- Maintain an execution history and report limitations.

The computer agent must not depend on a vision-language model. The preferred order of interface understanding is:

1. Application APIs or structured interfaces.
2. Browser DOM and accessibility information.
3. Operating-system accessibility interfaces.
4. Application-specific adapters.
5. OCR and deterministic image processing.
6. OpenCV template matching and coordinate-based interaction as fallbacks.

A vision-language model may be considered as an optional future capability, but it is not a required dependency.

### 2.4 Life Management Agent

The life-management agent handles personal organization and scheduled work.

It should be able to:

- Create and manage tasks and subtasks.
- Set reminders.
- Manage schedules and recurring activities.
- Track deadlines and commitments.
- Organize personal goals.
- Provide daily or weekly summaries.
- Follow up on tasks when appropriate.
- Integrate with calendars and notification services when configured.
- Receive requests from the companion and return results to it.

Examples include reminding the user to pay rent, tracking an assignment deadline, organizing a shopping list, or preparing a daily plan.

## 3. One application, one orchestration layer

The four agents should not become four unrelated applications. They should be specialized workers coordinated by one central orchestrator.

The central orchestrator should:

1. Receive the user's message or action.
2. Determine the intent and risk level.
3. Identify the appropriate agent or agents.
4. Provide only the context and permissions those agents need.
5. Track delegated work.
6. Coordinate dependencies and shared resources.
7. Collect verified results.
8. Return a clear response through the companion or relevant workspace.

Shared infrastructure includes model management, memory, tool execution, MCP connections, permissions, task persistence, scheduling, notifications, logging and verification.

---

# PART II — ARCHITECTURE AND TECHNICAL DECISIONS

## 4. Recommended architecture

Start with a **modular monolith**, not a distributed microservice system. Keep clear module boundaries so components can be separated later if scale or reliability requires it.

### 4.1 Desktop layer

- Tauri provides the installable desktop shell.
- React and TypeScript provide the user interface.
- Tailwind CSS provides styling.
- Tauri commands and events provide carefully scoped desktop integration.
- The frontend communicates with the backend through a documented API.

### 4.2 Backend layer

- Python hosts the application services.
- FastAPI exposes the local application API.
- Pydantic validates requests and structured data.
- WebSockets stream agent events, progress and live responses.
- A background worker or scheduler handles long-running and scheduled work.
- A persistent execution engine records progress independently of model context.

The backend should run as a managed child process or local service controlled by the desktop application. Define startup, readiness checks, shutdown, restart and crash-recovery behaviour explicitly.

### 4.3 Data layer

Recommended starting point:

- SQLite for local application data and initial single-user deployment.
- A migration layer such as Alembic or an equivalent migration strategy.
- A repository/data-access layer that prevents business logic from depending directly on SQLite-specific SQL.
- Local filesystem storage for large attachments, logs and model files.
- Optional PostgreSQL for deployments that genuinely need concurrent access, remote access or larger-scale operation.
- Optional vector search when semantic retrieval has a tested need; do not make it a prerequisite for the first working release.

This approach reduces installation complexity while keeping a path to more advanced storage.

### 4.4 AI model layer

Create a provider-independent model interface. Support local and cloud providers through adapters.

The common model interface should cover:

- Text generation and streaming.
- Structured output.
- Tool-call requests.
- Context-window metadata.
- Token usage where available.
- Cancellation.
- Timeouts and retries.
- Provider errors.
- Model capability declarations.

Possible local inference integration: llama.cpp. Cloud providers should be added through individual adapters. Never hard-code the whole application to one model vendor.

### 4.5 Automation layer

Use the best available interface for each operation:

- Native Linux APIs and D-Bus/GIO for system integration.
- AT-SPI2 for Linux accessibility where supported.
- xdg-desktop-portal interfaces for permission-mediated Wayland screen capture and remote input where available.
- Playwright for browser automation.
- LibreOffice UNO for supported LibreOffice automation.
- Windows UI Automation and COM/VBA for Windows-specific applications such as Microsoft Access.
- OCR and OpenCV for visual fallback workflows.

Do not assume a technique that works on X11 will work unchanged on GNOME Wayland.

### 4.6 MCP layer

MCP is an integration protocol, not the entire internal execution architecture.

Use native backend services for core internal operations. Expose selected capabilities through MCP when this makes them reusable by agents or external clients.

Support appropriate MCP transports, including local stdio and remote Streamable HTTP, according to the SDK and server capabilities in use.

Treat every external MCP server as a separate trust boundary. Inspect its configuration, tools, permissions and outputs before allowing agents to use it.

## 5. Suggested high-level module structure

```text
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

This is a proposed starting structure, not a requirement to create every directory on day one. Create modules when their phase begins.

---

# PART III — FRONTEND SPECIFICATION

## 6. Global application layout

Use a consistent, professional desktop design with:

- Collapsible left sidebar.
- Top navigation and global search.
- Main workspace.
- Optional contextual side panel.
- Status and activity area.
- Notification centre.
- Dark and light themes.
- Resizable panels.
- Keyboard shortcuts.
- Clear agent and connection status.
- Consistent loading, empty, error and confirmation states.

The interface should remain usable at common desktop resolutions and support long conversations, large project trees and extensive task lists.

## 7. Main navigation

Recommended destinations:

1. Home
2. Chat
3. Companion
4. Coding Agent
5. Computer Agent
6. Life Management
7. Tasks
8. Workspaces and Projects
9. Memory
10. MCP Servers
11. Models
12. Integrations
13. Activity and History
14. Settings

## 8. Screen requirements

### Home dashboard

Show:

- A natural greeting.
- Quick actions.
- Agent availability.
- Active and paused tasks.
- Pending approvals.
- Recent conversations.
- Recent projects.
- Upcoming reminders.
- MCP and model status.
- Recent activity.
- Optional system resource information.

Dashboard cards must use real backend data once the relevant services exist.

### Chat workspace

Include:

- Conversation list and search.
- Message history.
- Streaming responses.
- Markdown and code rendering.
- Attachments.
- Message editing and regeneration.
- Stop-generation control.
- Model and agent selection.
- Conversation creation, archive and deletion.
- Context and tool-activity indicators.

### Companion workspace

Include:

- Natural conversational interface.
- Personal profile and memory controls.
- Unresolved questions and discussion topics.
- Follow-up history.
- Goals and recurring commitments.
- Proactive engagement settings.
- Clear controls for quiet hours and frequency.

### Coding workspace

Include:

- Project/workspace selector.
- Conversation and task objective.
- Plan and persistent TODO panel.
- Project file explorer.
- Change review and diffs.
- Terminal output.
- Test results.
- Tool activity.
- Execution history.
- Approval requests.
- Start, pause, resume, stop and retry controls.

When a file is copied or changed, show the relevant source and destination or a meaningful diff where appropriate. Do not imply that file contents were moved unless the operation actually did so.

### Computer workspace

Include:

- Operating-system/session information.
- Active application and window.
- Available application adapters.
- Browser sessions.
- Automation sessions.
- Accessibility inspection.
- Screenshot and OCR inspection.
- Detected interface elements.
- Recent actions and verification results.
- Permission and approval requests.

### Life Management workspace

Include:

- Tasks and subtasks.
- Calendar/schedule views when an integration exists.
- Reminders.
- Recurring activities.
- Deadlines.
- Goals.
- Completion history.
- Daily and weekly summaries.

### MCP centre

Include:

- Server list and status.
- Add/edit/remove configuration.
- Connect/disconnect/restart.
- Discovered tools and schemas.
- Tool testing.
- Permissions.
- Health and logs.
- Credential configuration without displaying secret values.

### Memory centre

Include:

- Search.
- Memory categories.
- Memory details and source context.
- Edit/correct.
- Delete.
- Retention controls.
- Excluded topics.
- Related memories.
- Unresolved conversation items.

### Settings

Include:

- General.
- Appearance.
- Model providers.
- Local models.
- Cloud providers.
- Agent behaviour.
- Memory.
- Voice.
- Computer permissions.
- Browser settings.
- MCP.
- Integrations.
- Database and storage.
- Notifications and quiet hours.
- Privacy.
- Logs and diagnostics.
- Backup and restore.

Every control must have a defined behaviour, validation, error handling and feedback. Do not ship decorative controls that appear functional but do nothing.

---

# PART IV — DEVELOPMENT ROADMAP

Build in the order below. Each phase has a deliverable and acceptance tests. Do not advance merely because code has been written.

## PHASE 0 — Requirements, design and development preparation

### Objectives

- Finalize the first-release scope.
- Document architecture and module responsibilities.
- Identify operating-system constraints.
- Prepare the development environment.
- Establish repository and quality practices.

### Tasks

1. Write product requirements and user stories.
2. Define the four agents and their responsibilities.
3. Define shared services and agent permissions.
4. Define the first-release minimum viable product.
5. Draw component and data-flow diagrams.
6. Define API and WebSocket conventions.
7. Design initial database entities.
8. Decide how the desktop shell starts and manages the backend.
9. Identify dependencies and platform-specific components.
10. Create the Git repository and branch strategy.
11. Add formatting, linting and testing conventions.
12. Document setup and recovery procedures.

### Arch Linux preparation

Verify the required development tools independently:

- Git.
- A supported Python interpreter.
- Node.js and npm or pnpm.
- Rust and Cargo.
- Tauri prerequisites.
- A code editor.
- Browser testing dependencies.
- SQLite tooling.

Use a project virtual environment. Do not remove or replace the system Python simply to satisfy a project dependency. If a library does not support the installed Python version, use a separate supported interpreter for this project.

### Acceptance criteria

- Requirements are documented.
- Architecture boundaries are clear.
- Repository is initialized.
- Development environment is reproducible.
- First-release scope is agreed.

## PHASE 1 — Desktop shell and backend foundation

### Objectives

Create a real desktop application that starts reliably and communicates with its backend.

### Tasks

1. Initialize Tauri with React and TypeScript.
2. Configure application identity, window and build settings.
3. Create the main application shell.
4. Implement sidebar, top bar, main content and status area.
5. Add routing and theme support.
6. Create reusable UI components.
7. Create the Python backend and FastAPI application.
8. Add health and readiness endpoints.
9. Add structured logging and exception handling.
10. Implement managed backend startup and shutdown.
11. Add API client and WebSocket connection.
12. Display backend connection state.
13. Handle backend crash and restart cases.
14. Test development and production launch modes.

### Acceptance criteria

- Desktop application launches.
- Backend starts and reports readiness.
- Frontend can call the backend.
- WebSocket events reach the frontend.
- Shutdown does not leave unintended background processes.
- Connection failures are visible and recoverable.

## PHASE 2 — Frontend implementation

### Objectives

Build the navigation and complete screen structure with real service contracts.

### Tasks

1. Implement the design system and reusable components.
2. Build Home.
3. Build Chat.
4. Build Companion.
5. Build Coding Agent.
6. Build Computer Agent.
7. Build Life Management.
8. Build Tasks.
9. Build Workspaces and Projects.
10. Build Memory.
11. Build MCP management.
12. Build Models and Integrations.
13. Build Activity and History.
14. Build Settings.
15. Add loading, empty, error and confirmation states.
16. Add keyboard navigation and shortcuts.
17. Test accessibility and desktop layouts.

Use clearly labelled sample data only where a backend feature is not yet implemented. Do not simulate successful AI actions.

### Acceptance criteria

- All navigation destinations render.
- Forms validate.
- Every implemented control has a defined action.
- Screens behave correctly at target desktop sizes.
- No fake success messages or inert controls remain.

## PHASE 3 — Persistence and application data foundation

### Objectives

Persist conversations, settings and tasks before implementing advanced autonomy.

### Tasks

1. Configure SQLite and migrations.
2. Create repositories/data-access interfaces.
3. Design user settings and provider configuration records.
4. Create conversation and message records.
5. Create agent and task records.
6. Create execution and event records.
7. Create memory records and source references.
8. Create MCP server and permission records.
9. Add attachment metadata and filesystem storage.
10. Add backup and restore basics.
11. Test migrations and database recovery.

Keep database-specific operations behind the data-access layer so PostgreSQL can be introduced later if justified.

### Acceptance criteria

- Conversations survive application restarts.
- Settings persist.
- Tasks and execution records persist.
- Migrations can be applied and tested.
- Backup and restore work in a test environment.

## PHASE 4 — Model provider integration

### Objectives

Allow the application to use local and cloud models through one interface.

### Tasks

1. Define the model provider contract.
2. Define capabilities and model metadata.
3. Integrate a local llama.cpp provider.
4. Implement model loading and unloading.
5. Configure context and inference parameters.
6. Implement streaming and cancellation.
7. Add selected cloud provider adapters.
8. Securely store provider credentials.
9. Implement connection and model tests.
10. Add model selection UI.
11. Add routing based on capabilities, privacy, context and user preference.
12. Handle provider errors and context overflow.

Private data must not be sent to a cloud provider unless the configured policy and user authorization allow it.

### Acceptance criteria

- At least one configured local model responds.
- A configured cloud model responds if cloud support is included in the milestone.
- Streaming and cancellation work.
- Provider failures are handled.
- Model switching does not break conversation history.

## PHASE 5 — Security and permission foundation

### Objectives

Establish permission controls before giving models access to powerful tools.

### Tasks

1. Define permission categories: read, write, modify, delete, execute, install, network, credentials, financial and administrative.
2. Define permissions by agent, tool, resource and session.
3. Implement approval requests.
4. Implement narrowly scoped approvals.
5. Implement allowed-directory restrictions.
6. Implement secret storage.
7. Add audit records for sensitive operations.
8. Add timeouts and output limits.
9. Define trusted and untrusted input boundaries.
10. Add tests for unauthorized actions.

Use least privilege. Do not give a model unrestricted root access or unrestricted access to the user's entire filesystem.

### Acceptance criteria

- Unauthorized actions are blocked.
- Sensitive actions can request approval.
- Permissions are auditable.
- Credentials are not exposed in logs or model prompts.
- Each agent has only the capabilities it needs.

## PHASE 6 — Tool registry and execution engine

### Objectives

Allow models to request real, controlled operations.

### Tool contract

Each tool defines:

- Stable identifier and name.
- Description.
- Input schema.
- Output schema.
- Permission requirements.
- Timeout and resource limits.
- Execution implementation.
- Verification method.
- Error behaviour.

### Tasks

1. Build tool registration and discovery.
2. Validate tool arguments.
3. Implement permission checks.
4. Implement execution and cancellation.
5. Normalize tool results.
6. Record tool calls and results.
7. Implement initial filesystem tools.
8. Implement time and system-information tools.
9. Implement controlled process inspection.
10. Implement controlled command execution.
11. Add post-action verification.
12. Add tool tests and failure handling.

Start with low-risk read operations. Add writes and destructive actions only after permission and verification mechanisms work.

### Acceptance criteria

- Model can request a registered tool.
- Backend validates and executes the request.
- Unauthorized operations are rejected.
- Results and errors are recorded.
- Important changes are independently verified.

## PHASE 7 — Planning, TODOs and persistent agent execution

### Objectives

Turn model responses into durable multi-step work.

### Tasks

1. Define task, subtask and dependency schemas.
2. Build natural-language request decomposition.
3. Extract objective, expected outcome, risks and missing information.
4. Generate a structured plan.
5. Create persistent TODOs.
6. Track dependencies and blockers.
7. Build the agent execution loop.
8. Add pause, resume, stop and retry.
9. Persist checkpoints.
10. Restore execution state after restart.
11. Detect duplicate or interrupted operations.
12. Produce completion reports with verification evidence.

### Execution cycle

1. Load objective and current state.
2. Select the next executable task.
3. Gather only relevant context.
4. Request a proposed action from the model.
5. Validate action and permissions.
6. Execute the action.
7. Observe and verify the result.
8. Update task and execution state.
9. Replan if required.
10. Continue until complete, blocked or stopped.

### Acceptance criteria

- Agent can complete a multi-step low-risk workflow.
- TODOs persist across restarts.
- Failed tasks can be retried.
- Interrupted work can be resumed safely.
- Completion reports distinguish verified work from incomplete work.

## PHASE 8 — MCP client and server infrastructure

### Objectives

Connect NEXUS AI to selected external MCP tools and expose selected internal capabilities.

### Tasks

1. Integrate a maintained MCP SDK.
2. Implement server configuration.
3. Implement stdio connections.
4. Implement remote Streamable HTTP connections where required.
5. Implement initialization and capability negotiation.
6. Discover tools, resources and prompts where supported.
7. Validate tool schemas.
8. Invoke tools through the permission system.
9. Handle connection loss and reconnection.
10. Add server health and logs.
11. Add tool-level allowlists.
12. Add server isolation and trust controls.

### Initial custom MCP servers or adapters

Build only when there is a clear need; reuse trusted existing servers when they meet requirements.

- Filesystem capabilities.
- Terminal capabilities.
- Browser capabilities.
- Database capabilities.
- Git capabilities.
- Computer automation capabilities.
- Task and memory capabilities.

These may be independent MCP servers, or selected internal services exposed through MCP wrappers. Do not duplicate the core execution engine inside each server.

### Acceptance criteria

- NEXUS AI connects to a test MCP server.
- It discovers and inspects tools.
- It invokes authorized tools.
- Invalid schemas and failed connections are handled.
- Tool calls are logged and permission-checked.

## PHASE 9 — Arch Linux and GNOME computer integration

### Objectives

Give the computer agent controlled access to the initial operating system.

### Tasks

1. Detect distribution, kernel, architecture and desktop session.
2. Detect GNOME and Wayland.
3. Implement filesystem operations.
4. Implement application discovery and launching.
5. Implement process inspection.
6. Implement system resource inspection.
7. Integrate D-Bus and GIO where appropriate.
8. Investigate AT-SPI2 accessibility support.
9. Implement desktop notifications.
10. Build a pacman adapter.
11. Add explicit approval for package installation/removal and privileged operations.
12. Test on the actual target desktop.

### Acceptance criteria

- Agent can inspect system information.
- Agent can locate and organize authorized files.
- Agent can launch selected applications.
- Agent can inspect permitted processes.
- Package operations follow approval policies.

## PHASE 10 — Browser automation

### Objectives

Enable reliable web interaction without relying on screenshots for ordinary browser tasks.

### Tasks

1. Integrate Playwright.
2. Manage browser profiles and sessions.
3. Implement tab and navigation management.
4. Extract page title, URL and relevant DOM.
5. Use accessible names and roles to locate elements.
6. Implement click, fill, select, scroll and navigation.
7. Implement downloads and uploads with restrictions.
8. Detect login requirements and expired sessions.
9. Handle dynamic pages and timeouts.
10. Verify actions and downloaded files.
11. Treat page content as untrusted input.
12. Require user involvement for CAPTCHA and other access controls; do not bypass them.

### Acceptance criteria

- Agent can complete a controlled browser workflow.
- It can explain when login or user intervention is required.
- Downloads are verified.
- Malicious page instructions cannot grant themselves permissions.

## PHASE 11 — GUI understanding: accessibility, OCR and OpenCV

### Objectives

Support applications where APIs or browser DOM are unavailable.

### Tasks

1. Investigate Wayland-compatible screen capture through xdg-desktop-portal.
2. Implement permission-mediated screenshot capture.
3. Detect monitors, resolution and scaling.
4. Integrate Tesseract OCR.
5. Extract text and bounding boxes.
6. Integrate OpenCV template matching.
7. Support template registration and versioning.
8. Inspect AT-SPI2 accessibility trees where available.
9. Combine accessibility, OCR, templates and window metadata.
10. Build structured interface descriptions.
11. Implement controlled input through supported desktop mechanisms.
12. Verify each important GUI action.

### Recognition priority

Prefer accessibility information and application metadata. Use OCR and image matching when necessary. Coordinate-based interaction should be treated as fragile and require strong verification.

### Acceptance criteria

- Agent can inspect a test application window.
- It can identify supported controls using structured information.
- It can perform a small set of verified GUI operations.
- It reports uncertainty rather than guessing when controls cannot be identified.

## PHASE 12 — Application adapter framework

### Objectives

Make application support modular and extensible.

### Adapter contract

Each adapter should declare:

- Application identifier and supported versions.
- Detection method.
- Capabilities.
- Required dependencies.
- API or accessibility integration.
- Supported operations.
- Permissions.
- Verification rules.
- Known limitations.

### Initial adapters

1. Terminal.
2. GNOME Files.
3. Firefox.
4. LibreOffice Writer and Calc.
5. LibreOffice Base.
6. Microsoft Access on Windows.

For LibreOffice, investigate UNO automation. For Microsoft Access, use Windows-specific COM/VBA or UI Automation where appropriate. Microsoft Access is not a native Arch Linux application; support it through a separate Windows adapter or supported remote Windows environment.

### Tasks

- Build adapter registry and lifecycle.
- Implement application detection.
- Add capability discovery.
- Add adapter-specific tests.
- Add version compatibility checks.
- Add adapter development templates and documentation.
- Add accessibility/OCR fallback for applications without suitable APIs.

### Acceptance criteria

- At least two initial application adapters work reliably.
- New adapters can be added without rewriting the orchestrator.
- Unsupported operations are clearly reported.

## PHASE 13 — Autonomous coding agent

### Objectives

Combine workspace understanding, planning, tools, terminal execution and verification into a software engineering agent.

### Tasks

1. Build workspace registration and selection.
2. Scan project structure.
3. Detect languages, frameworks and package managers.
4. Index relevant files and symbols.
5. Search code and configuration.
6. Build context selection and context-size controls.
7. Implement safe file creation and editing.
8. Implement structured patches and diff review.
9. Integrate terminal execution.
10. Discover and run tests.
11. Run formatters and linters.
12. Parse stack traces and build errors.
13. Implement debugging and repair loops.
14. Integrate Git status, diffs and branches.
15. Add project-specific memory.
16. Add checkpoint and recovery.
17. Produce a verified change report.

Start with a small set of languages and frameworks, then expand based on tests and actual usage.

### Acceptance criteria

- Agent can inspect an existing project.
- It can implement a bounded feature.
- It can run relevant tests.
- It can diagnose and correct a controlled failure.
- It can show exactly which files changed.
- It does not claim tests passed unless they actually passed.

## PHASE 14 — Conversational companion and personal memory

### Objectives

Build the full companion experience, not just a chat interface.

### Tasks

1. Implement conversation persistence and retrieval.
2. Implement conversation summaries.
3. Implement working memory for the current discussion.
4. Implement a user-controlled personal profile.
5. Implement long-term memory categories.
6. Implement semantic retrieval when useful.
7. Implement episodic memory for important events.
8. Track unresolved questions and topics.
9. Track promises, plans and pending decisions.
10. Add statuses: open, waiting for user, waiting for event, completed, cancelled and expired.
11. Implement follow-up relevance and timing rules.
12. Implement conversational intent classification.
13. Distinguish casual chat from requests and tasks.
14. Add appropriate emotional-context recognition.
15. Add varied, natural short responses.
16. Add memory inspection, correction and deletion.
17. Add exclusions and retention settings.
18. Add opt-in proactive conversation with quiet hours and frequency limits.

### Example behaviour

If the user previously mentioned an assignment and later returns, the companion may ask how the assignment is progressing when that is relevant. It should not repeatedly bring up a topic that has been resolved, is no longer relevant, or that the user has asked it to avoid.

If the user says, "I have several things to do," the companion can ask what needs attention. Once the user identifies actionable tasks, it can offer to organize them through the Life Management Agent.

### Acceptance criteria

- Conversation context survives application restarts.
- Relevant memories can be retrieved.
- Unresolved items can be tracked and resolved.
- Follow-ups are contextually appropriate and not repetitive.
- Users can inspect and control stored memories.
- Casual messages are not automatically converted into tasks.

## PHASE 15 — Life Management Agent and agent orchestration

### Objectives

Complete personal organization and coordinate the four agents.

### Life Management tasks

1. Implement task and subtask management.
2. Implement due dates and reminders.
3. Implement recurring schedules.
4. Implement notification delivery.
5. Add calendar integration when configured.
6. Add daily and weekly summaries.
7. Add deadline and commitment tracking.
8. Add companion handoff.
9. Add completion and snooze actions.

### Orchestration tasks

1. Implement request classification and routing.
2. Define agent capability declarations.
3. Implement structured agent-to-agent requests.
4. Implement context sharing with access policies.
5. Implement task delegation and result aggregation.
6. Add resource locks and conflict handling.
7. Prevent duplicate execution.
8. Track agent status and progress.
9. Handle agent timeouts and failures.
10. Return verified results to the companion.

### Acceptance criteria

- Companion can delegate an organizational request.
- Life Management Agent creates and tracks a reminder or task.
- Orchestrator can delegate a coding task.
- Coding agent can return a structured result.
- Companion can explain the outcome accurately.
- Agents cannot access unauthorized memories or tools.

## PHASE 16 — Voice and proactive assistance

### Objectives

Add optional voice interaction and background assistance after text workflows are reliable.

### Tasks

1. Integrate speech recognition, such as a supported Whisper implementation.
2. Add microphone selection and permissions.
3. Add voice activity detection.
4. Add transcription and language settings.
5. Integrate a text-to-speech engine such as Piper.
6. Add voice selection and playback controls.
7. Support interruption and cancellation.
8. Add explicit listening indicators.
9. Add optional wake-word or continuous-listening behaviour only with clear opt-in.
10. Add scheduled notifications and daily summaries.
11. Add background worker lifecycle and quiet hours.
12. Ensure proactive actions cannot silently perform sensitive operations.

### Acceptance criteria

- Voice input can be enabled and disabled.
- Transcription and speech output work.
- The user can interrupt speech.
- Microphone use is visible and permission-controlled.
- Scheduled notifications work under documented desktop-session limitations.

## PHASE 17 — Production hardening, packaging and release

### Objectives

Make NEXUS AI safe, recoverable, installable and maintainable.

### Security and reliability

1. Complete permission and audit coverage.
2. Review credential storage.
3. Isolate external MCP servers and untrusted tools.
4. Add filesystem and process restrictions.
5. Defend against prompt injection from websites, documents, emails, app screens and tool outputs.
6. Add resource limits and timeouts.
7. Add crash recovery and database backup.
8. Add migration tests.
9. Add log rotation and diagnostics.
10. Add privacy and data-retention controls.

### Testing

Implement:

- Unit tests.
- Integration tests.
- API tests.
- Frontend tests.
- Database migration tests.
- MCP protocol tests.
- Browser automation tests.
- GUI recognition tests.
- Application adapter tests.
- Agent workflow tests.
- Security tests.
- Performance tests.
- End-to-end tests.
- Clean-install tests.

### Packaging

1. Build the production frontend.
2. Package the Tauri application.
3. Bundle or provision the backend appropriately.
4. Check required system dependencies.
5. Initialize application storage.
6. Run database migrations.
7. Configure secure settings.
8. Add desktop entry and icon.
9. Add update and rollback procedures.
10. Test on a clean Arch Linux environment.
11. Document installation, backup, restore and troubleshooting.

### Acceptance criteria

- Application installs and launches on a clean supported environment.
- Backend lifecycle is managed by the desktop application.
- Data survives restart and supported upgrades.
- Critical tests pass.
- Failures are logged and recoverable.
- Users can back up and restore their data.

---

# PART V — CROSS-CUTTING ENGINEERING REQUIREMENTS

## 9. Persistent execution state

Never rely on an LLM conversation alone to remember a long-running task.

Every execution should persist:

- Execution ID.
- Agent ID.
- User objective.
- Plan version.
- Current task.
- Completed and pending tasks.
- Tool calls and results.
- Errors and retries.
- Checkpoints.
- Approval and permission decisions.
- Verification evidence.
- Final report.

After a crash, reconstruct the execution from persistent state. Before retrying an operation, determine whether it already succeeded to avoid duplicate side effects.

## 10. Event-driven updates

Publish structured events for important operations, such as:

```text
agent.started
agent.planning
agent.delegated
task.created
task.started
task.completed
task.blocked
tool.called
tool.failed
tool.verified
mcp.connected
mcp.disconnected
computer.action_started
computer.action_verified
memory.created
conversation.followup_detected
approval.requested
approval.granted
approval.denied
agent.completed
```

The frontend should receive relevant events through WebSockets and display understandable activity summaries.

## 11. Permission and approval policy

Use least privilege and narrowly scoped permissions.

Examples:

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

Allow harmless, reversible operations within user-approved scopes. Require confirmation for destructive, privileged, financial, credential-sensitive or externally consequential operations. Log the authorization decision.

## 12. Untrusted content and prompt injection

Treat website content, documents, emails, screenshots, terminal output, downloaded files and external MCP responses as untrusted data.

Such content may provide information for a task, but must not be allowed to override system policy, change permissions, expose secrets or authorize unrelated actions.

## 13. Observability

Record:

- Agent and task status.
- Selected actions and concise action explanations.
- Tool calls and results.
- Execution duration.
- Errors and retries.
- Model/provider usage.
- Token usage when available.
- MCP connection events.
- Permission decisions.
- Verification outcomes.

Show useful plans, actions and results. Do not expose private internal reasoning traces.

## 14. Reliability principles

- Every long-running operation has a persistent execution ID.
- Every tool has input validation and a timeout.
- Every important side effect has a verification step.
- Every risky action has an approval policy.
- Every agent can be stopped.
- Every failed task has a clear state.
- Every external integration can be disconnected.
- Every stored memory has user controls.
- Every feature has tests and documented limitations.

---

# PART VI — DELIVERY STRATEGY

## 15. Five practical delivery milestones

### Milestone 1 — Working desktop foundation

Phases 0–4.

**Deliverable:** A desktop application with a reliable backend, persistent conversations and configurable local/cloud model access.

### Milestone 2 — Safe tool-using agent

Phases 5–8.

**Deliverable:** Permission-controlled tools, planning, persistent TODOs, recoverable executions and MCP integration.

### Milestone 3 — Computer operation

Phases 9–12.

**Deliverable:** Arch Linux integration, browser automation, GUI understanding and modular application adapters.

### Milestone 4 — Personal AI environment

Phases 13–16.

**Deliverable:** Autonomous coding, natural conversational companion, personal memory, Life Management Agent, multi-agent orchestration and optional voice.

### Milestone 5 — Production release

Phase 17.

**Deliverable:** A tested, secure, installable and recoverable desktop application.

## 16. Rules for moving between phases

Do not move to the next phase simply because implementation code exists.

A phase is complete only when:

1. Its required features work.
2. Its acceptance tests pass.
3. Errors are handled.
4. Permissions are enforced.
5. Documentation is updated.
6. The application remains usable after restart.
7. The completed work is committed to Git.
8. Known limitations are recorded.

---

# PART VII — IMPORTANT PLATFORM AND SCOPE DECISIONS

## 17. Initial platform and future portability

The first implementation target is Arch Linux with GNOME and Wayland. Keep platform-specific operations behind interfaces so Windows support can be added without rewriting the agents.

Examples:

- Linux system adapter: D-Bus, GIO, AT-SPI2 and Wayland-compatible portals.
- Windows system adapter: Windows APIs, UI Automation and COM where appropriate.
- Browser adapter: Playwright across supported platforms.
- Application adapters: application-specific implementations.

Microsoft Access requires Windows. On Arch Linux, use LibreOffice Base for the initial database-application automation work. Do not promise native Access automation on Arch.

## 18. Do not overbuild the first release

The final vision is broad. The first usable release should be narrower.

Recommended first-release capabilities:

- Installable desktop shell.
- Backend lifecycle management.
- Persistent chat.
- One local model provider.
- Optional one cloud provider.
- Basic companion memory with user controls.
- Safe filesystem tools.
- Controlled terminal tool.
- Task planning and persistent TODOs.
- One MCP integration.
- Basic browser automation.
- Clear approval and activity history.

Then add advanced GUI automation, application adapters, full coding autonomy, life-management integrations, proactive engagement and voice incrementally.

## 19. Suggested technology choices

| Area | Starting choice |
|---|---|
| Desktop shell | Tauri |
| Frontend | React + TypeScript |
| Styling | Tailwind CSS |
| Backend | Python + FastAPI |
| Validation | Pydantic |
| Initial database | SQLite |
| Database migrations | Alembic or equivalent |
| Local inference | llama.cpp |
| Browser automation | Playwright |
| OCR | Tesseract |
| Image processing | OpenCV |
| Linux accessibility | AT-SPI2 |
| Linux desktop integration | D-Bus / GIO |
| Wayland capture/input | xdg-desktop-portal interfaces |
| LibreOffice automation | UNO |
| Windows automation | UI Automation / COM |
| MCP | Maintained official SDK |
| Testing | pytest and frontend testing tools |
| Scheduling | Background worker or scheduler |

These are starting recommendations, not a requirement to install every dependency immediately.

---

# PART VIII — FINAL PRODUCT EXPERIENCE

## 20. Example: autonomous software development

The user says:

> Create a complete e-commerce application, organize its files, configure its database, test it and prepare it for deployment.

NEXUS AI should:

1. Understand the objective.
2. Ask for missing essential requirements.
3. Create a project plan.
4. Generate persistent TODOs.
5. Select the coding agent.
6. Inspect the computer and chosen workspace.
7. Prepare the project environment.
8. Use authorized tools and MCP integrations.
9. Create and modify application files.
10. Configure the database.
11. Run tests and builds.
12. Diagnose and correct failures.
13. Verify the application.
14. Save execution state.
15. Present changed files, test results, limitations and next steps.

## 21. Example: natural companion conversation

The user says:

> Hey, how are you?

The companion responds naturally and briefly, using the current conversational context.

If the user later says:

> I have an assignment, several downloads to organize and rent to pay.

The companion should understand that this is a mixture of conversation and actionable work. It can ask a useful clarifying question, offer to organize the tasks, and delegate a rent reminder to the Life Management Agent once the necessary date is known.

It should not invent a reminder, claim it has been scheduled when it has not, or turn unrelated casual conversation into tasks.

## 22. Example: computer operation

The user says:

> Open LibreOffice Base, create a database for my assignment and create the required tables.

NEXUS AI should:

1. Confirm the relevant assignment requirements if they are not available.
2. Select the computer agent and LibreOffice Base adapter.
3. Open the application.
4. Create the database.
5. Create the tables using supported automation.
6. Verify that the tables exist.
7. Save the database.
8. Report the actual file location and completed operations.

## 23. The final definition

NEXUS AI is an autonomous personal AI operating environment delivered as a standalone desktop application.

It combines:

- A natural conversational companion that remembers relevant context and follows up appropriately.
- An autonomous coding agent that can develop and test software.
- A computer agent that can operate the user's computer and supported applications.
- A life-management agent that organizes tasks, reminders and schedules.
- A central orchestrator that coordinates these agents.
- Shared memory, model management, tools, MCP integrations, permissions, execution history and verification.

The initial target is Arch Linux with GNOME and Wayland. Portability should be designed into the architecture from the beginning, while actual support for each additional platform is delivered through tested platform adapters.

**The governing principle:** NEXUS AI must not merely tell the user what to do. It should be able to carry out authorized work, verify what happened, preserve its progress and communicate the result honestly.

---

# RECOMMENDED FIRST DEVELOPMENT SESSION

Start with Phase 0, then implement only the first vertical slice of Phase 1:

1. Inspect the development environment.
2. Create the repository.
3. Initialize Tauri with React and TypeScript.
4. Create the FastAPI backend.
5. Make Tauri manage the backend lifecycle.
6. Add a health-check endpoint.
7. Display backend connection status in the desktop UI.
8. Test startup, shutdown and restart.
9. Commit the working foundation.

Do not begin by implementing all agents, MCP servers or GUI automation at once. Build one reliable layer at a time, test it, document it and then continue.
