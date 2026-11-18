# PHASE 6 — MCP infrastructure and custom MCP servers

## Objective

Make the application capable of discovering and communicating with external MCP servers, while also creating its own specialized MCP servers.

### Step 6.1 — Implement the MCP client manager

Implement:

- MCP server configuration.
- Connection management.
- Initialization.
- Capability negotiation.
- Tool discovery.
- Resource discovery.
- Prompt discovery where supported.
- Tool invocation.
- Response parsing.
- Connection monitoring.
- Reconnection.
- Error handling.

Support appropriate MCP transports, including local stdio and remote Streamable HTTP.

### Step 6.2 — Create the MCP server registry

Store:

- Server identifier.
- Server name.
- Description.
- Transport type.
- Executable or endpoint.
- Arguments.
- Environment configuration.
- Authentication configuration.
- Connection state.
- Discovered tools.
- Permissions.

### Step 6.3 — Build the first custom MCP server: Filesystem

Responsibilities:

- List directories.
- Read files.
- Write files.
- Create directories.
- Search files.
- Inspect metadata.
- Move and copy files.

Security requirements:

- Restrict access to authorized directories.
- Prevent path traversal.
- Apply file-size limits.
- Validate operations.
- Protect sensitive locations.

### Step 6.4 — Build the second custom MCP server: Terminal

Responsibilities:

- Execute authorized commands.
- Retrieve command output.
- Inspect processes.
- Retrieve system information.
- Manage permitted processes.
- Capture execution errors.

Implement command policies, execution timeouts, process isolation and explicit approval for privileged operations.

Never expose unrestricted root access to the model.

### Step 6.5 — Build the third custom MCP server: Browser

Responsibilities:

- Create browser sessions.
- Navigate websites.
- Inspect pages.
- Retrieve accessibility information.
- Click elements.
- Fill forms.
- Download files.
- Capture page information.
- Manage tabs.

Use Playwright where appropriate.

### Step 6.6 — Build the fourth custom MCP server: Database

Responsibilities:

- Connect to authorized databases.
- Inspect schemas.
- List tables.
- Execute permitted queries.
- Create tables.
- Retrieve records.
- Inspect database errors.

Implement read-only access by default, with separate approval for database modifications.

### Step 6.7 — Build the fifth custom MCP server: Git

Responsibilities:

- Inspect repositories.
- Check status.
- Read diffs.
- Create branches.
- Commit changes.
- Inspect history.
- Manage permitted repository operations.

### Step 6.8 — Build the sixth custom MCP server: Computer Automation

Responsibilities:

- Inspect active windows.
- Identify applications.
- Capture screenshots.
- Retrieve accessibility information.
- Request permitted keyboard operations.
- Request permitted mouse operations.
- Inspect detected interface elements.

This server should communicate with the dedicated computer automation service rather than directly implementing every desktop interaction itself.

### Step 6.9 — Build the seventh custom MCP server: Task and Memory

Responsibilities:

- Create tasks.
- Retrieve TODOs.
- Update task statuses.
- Retrieve previous task information.
- Search authorized memories.
- Store approved memories.
- Retrieve unresolved conversation topics.

### Step 6.10 — Integrate external MCP servers

Investigate and connect suitable existing servers for:

- GitHub.
- Documentation.
- Search.
- Cloud storage.
- Additional databases.
- Other developer services.

Do not create a replacement for every existing MCP server. Reuse trusted implementations when they satisfy the requirements.

### Step 6.11 — MCP security

Implement:

- Server allowlisting.
- Tool-level permissions.
- Credential isolation.
- Authentication management.
- Connection limits.
- Tool timeouts.
- Output validation.
- Server health monitoring.
- Audit trails.

### Step 6.12 — MCP testing

Test each server independently before exposing its tools to the AI.

Verify initialization, discovery, schema validation, tool calls, errors, disconnection and reconnection.

**Completion criteria:** NEXUS AI can manage multiple MCP servers, discover their tools, call them and safely use their results in autonomous workflows.

---


**Roadmap:** [Index](../../overview) · [← Phase 5: Planning, TODO and autonomous execution engine](phase-05.md) · [Phase 7: Operating-system agent →](phase-07.md)
