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

## 5. Initial custom MCP servers (build on need)

1. Filesystem — list, read, write, create, search, metadata, move, copy
2. Terminal — execute commands, retrieve output, inspect processes
3. Browser — sessions, navigation, page inspection, clicks, forms, downloads
4. Database — connect, inspect schema, execute permitted queries
5. Git — inspect repo, status, diffs, branches, commits
6. Computer Automation — windows, screenshots, accessibility, input
7. Task and Memory — create tasks, retrieve TODOs, search memories

Custom servers may be independent MCP processes or internal services exposed through MCP wrappers. Do not duplicate the core execution engine inside each server.

## 6. External MCP server integration

Investigate and connect trusted existing servers for: GitHub, documentation, search, cloud storage, additional databases, developer services. Reuse trusted implementations rather than building replacements.

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
