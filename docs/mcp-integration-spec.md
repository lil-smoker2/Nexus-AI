# NEXUS AI — MCP Integration Specification

**Status:** Draft — Phase 0, Step 0.5  
**Source:** NEXUS_AI_Revised_Master_Roadmap.md, PART II Section 4.6

## 1. MCP role in architecture

MCP (Model Context Protocol) is an integration protocol, **not** the entire internal execution architecture.

- Native backend services handle core internal operations.
- Selected capabilities are exposed through MCP when reusable by agents or external clients.
- Supports stdio and Streamable HTTP transports.
- Every external MCP server is a separate trust boundary — inspect configuration, tools, permissions and outputs before allowing agent use.

## 2. MCP client manager responsibilities

| Responsibility | Description |
|---|---|
| Server configuration | Store server id, name, transport, endpoint, args, env, auth |
| Connection management | Connect, disconnect, restart, health monitoring |
| Initialization | MCP initialize handshake, capability negotiation |
| Tool discovery | List available tools, input/output schemas |
| Resource discovery | List available resources |
| Prompt discovery | List available prompts (where supported) |
| Tool invocation | Call tools through the permission system |
| Response parsing | Parse MCP responses into normalized format |
| Connection monitoring | Detect disconnection, trigger reconnection |
| Error handling | Timeouts, invalid schemas, server errors |
| Reconnection | Exponential backoff reconnection |

## 3. MCP server registry (stored in database)

| Field | Type | Notes |
|---|---|---|
| id | UUID | Server identifier |
| name | TEXT | Display name |
| description | TEXT | |
| transport | TEXT | stdio / streamable_http |
| endpoint | TEXT | Executable path or URL |
| args | JSON | Command-line arguments |
| env | JSON | Environment variables |
| auth_config | JSON | Authentication configuration |
| connection_state | TEXT | connected / disconnected / error |
| discovered_tools | JSON | Tools discovered from server |
| permissions | JSON | Tool-level allowlist |
| created_at | TIMESTAMP | |
| updated_at | TIMESTAMP | |

## 4. MCP security

| Control | Description |
|---|---|
| Server allowlisting | Only approved servers may connect |
| Tool-level permissions | Each tool requires explicit agent permission |
| Credential isolation | Secrets stored separately, never logged |
| Authentication management | Per-server auth config |
| Connection limits | Max concurrent connections per server |
| Tool timeouts | Per-tool execution timeout |
| Output validation | Validate tool outputs against schema |
| Server health monitoring | Track connectivity and error rates |
| Audit trails | Log all MCP tool calls and responses |

## 5. Domain MCP specifications (divided by MCP)

MCPs are split into per-domain specs under [`docs/mcp/`](./mcp/). Each spec defines scope, prerequisites, operations/tools, safety/verification, and (where applicable) a step-by-step guide to create the MCP.

| MCP | Spec | Operations summary |
|---|---|---|
| Filesystem | [mcp/filesystem.md](./mcp/filesystem.md) | **File & directory ops:** create file/dir, read, write/edit/append, delete file/dir, copy, move/rename, list, search/glob/content search, stat/exists. Includes **step-by-step MCP creation** (scope/roots & permissions → scaffold/transport → initialize & `tools/list` → implement handlers with path validation → verify/audit → register → test) and example schemas/flows. |
| Terminal | [mcp/terminal.md](./mcp/terminal.md) | Execute commands, retrieve/stream output, inspect/kill managed processes (policy-gated). |
| Browser | [mcp/browser.md](./mcp/browser.md) | Sessions, navigation, page/DOM inspection, click/type/select/submit, waits, downloads, screenshots. |
| Database | [mcp/database.md](./mcp/database.md) | List connections, inspect schema, execute permitted (parameterized/bounded) queries, explain. |
| Git | [mcp/git.md](./mcp/git.md) | Status/diff/log/show/branches (inspect) and gated add/commit/checkout/push/pull operations. |
| Computer Automation | [mcp/computer-automation.md](./mcp/computer-automation.md) | Session/window/app inspection, capture/accessibility/OCR, gated focus/launch/input actions. |
| Task and Memory | [mcp/task-memory.md](./mcp/task-memory.md) | Task/TODO create/update/list/status and memory store/search/retrieve/update/delete. |

Custom servers may be independent MCP processes or internal services exposed through MCP wrappers. Do not duplicate the core execution engine inside each server. See [mcp/README.md](./mcp/README.md) for the index.

## 6. External MCP server integration

Investigate and connect trusted existing servers for: GitHub, documentation, search, cloud storage, additional databases, developer services. Reuse trusted implementations rather than building replacements.

## 6.1 Frontend presentation

The chat context panel may present the status of an MCP-backed action as a concise, user-facing activity summary. It must not expose raw credentials, hidden model reasoning, or unvalidated server output. Show a result as complete only after the backend reports the tool outcome and any required verification; surface failures and permission requests explicitly. The chat layout and context-panel behavior are specified in [chat-experience.md](./chat-experience.md).

## 7. Tool contract via MCP

Each MCP tool exposed to agents defines:
- Stable identifier and name
- Description
- Input schema (JSON Schema)
- Output schema (JSON Schema)
- Permission requirements
- Timeout and resource limits
- Execution implementation (MCP server side)
- Verification method
- Error behaviour

## 8. MCP testing

Test each server independently before exposing tools to agents:
- Initialization handshake
- Tool/resource/prompt discovery
- Schema validation
- Tool calls (success and error cases)
- Disconnection and reconnection
- Permission enforcement

## 9. Data flow — MCP tool call

```
Agent requests tool → Orchestrator → Permission check → MCP Client → 
MCP Server (stdio/HTTP) → Tool result → Verification → Record → Agent
```

## 10. Configuration example

```json
{
  "servers": [
    {
      "id": "filesystem-local",
      "name": "Local Filesystem",
      "transport": "stdio",
      "endpoint": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/home/david/documents"],
      "permissions": ["read", "write", "list"],
      "timeout_ms": 30000
    }
  ]
}
```
