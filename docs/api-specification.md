# NEXUS AI — API Specification

**Status:** Draft — Phase 0, Step 0.5  
**Source:** NEXUS_AI_Revised_Master_Roadmap.md, PART II Section 8

## 1. Convention overview

- Framework: FastAPI (Python)
- Validation: Pydantic
- Base path: `/api/v1`
- Format: JSON
- HTTP status codes: standard RFC 7231
- CORS: configured for development; restricted in production
- Authentication: session/token-based (defined in Phase 5 security)

## 2. Common response envelope

All successful responses follow this envelope:

```json
{
  "data": { ... },
  "meta": {
    "request_id": "uuid",
    "timestamp": "2026-11-15T07:00:00Z",
    "version": "1.0.0"
  }
}
```

Error responses:

```json
{
  "error": {
    "code": "validation_error",
    "message": "Human-readable description",
    "details": { ... }
  },
  "meta": {
    "request_id": "uuid",
    "timestamp": "2026-11-15T07:00:00Z"
  }
}
```

## 3. Endpoint categories

| Category | Base path | Description |
|---|---|---|
| Health | `/health` | Liveness and readiness |
| Version | `/version` | Application version |
| Conversations | `/api/v1/conversations` | CRUD for conversations |
| Messages | `/api/v1/messages` | Send and retrieve messages |
| Agents | `/api/v1/agents` | Agent status and capability |
| Executions | `/api/v1/executions` | Execution state and control |
| Tasks | `/api/v1/tasks` | Task and TODO management |
| Memories | `/api/v1/memories` | Memory CRUD and search |
| MCP | `/api/v1/mcp` | Server config and tool discovery |
| Tools | `/api/v1/tools` | Tool registry and invocation |
| Permissions | `/api/v1/permissions` | Permission and approval |
| Models | `/api/v1/models` | Model provider management |
| Settings | `/api/v1/settings` | User settings |

## 4. Key endpoints (draft)

### 4.1 Health

`GET /health` → `{ status: "ok", backend: "ready", database: "connected" }`

### 4.2 Version

`GET /version` → `{ version: "0.1.0", build: "..." }`

### 4.3 Conversations

`GET /api/v1/conversations` → list of conversations  
`POST /api/v1/conversations` → create conversation  
`GET /api/v1/conversations/{id}` → conversation detail  
`DELETE /api/v1/conversations/{id}` → delete conversation

### 4.4 Messages

`POST /api/v1/messages` → send a message (returns assistant response or streams via WebSocket)  
`GET /api/v1/conversations/{id}/messages` → message history

The chat client renders messages in the central conversation area and may display separately authorized activity summaries and saved memories in its context panel. These are distinct from message content. Do not return or stream hidden chain-of-thought, private system prompts, credentials, or unrestricted internal traces as chat or context-panel data.

### 4.5 Executions

`GET /api/v1/executions` → list executions  
`GET /api/v1/executions/{id}` → execution state  
`POST /api/v1/executions/{id}/pause` → pause execution  
`POST /api/v1/executions/{id}/resume` → resume execution  
`POST /api/v1/executions/{id}/stop` → stop execution

### 4.6 Tasks

`GET /api/v1/tasks` → list tasks  
`POST /api/v1/tasks` → create task  
`PATCH /api/v1/tasks/{id}` → update task (status, priority, etc.)  
`DELETE /api/v1/tasks/{id}` → delete task

### 4.7 Tools

`GET /api/v1/tools` → list registered tools  
`POST /api/v1/tools/{id}/invoke` → invoke a tool (permission-checked)

### 4.8 Memories

`GET /api/v1/memories` → list/search memories  
`POST /api/v1/memories` → create memory  
`PATCH /api/v1/memories/{id}` → correct memory  
`DELETE /api/v1/memories/{id}` → delete memory

### 4.9 Permissions / Approvals

`GET /api/v1/permissions` → list permissions by agent/tool  
`POST /api/v1/approvals` → request approval  
`PATCH /api/v1/approvals/{id}` → grant/deny approval

## 5. WebSocket events

WebSocket endpoint: `ws/api/v1/events`

Events streamed to the frontend for live monitoring:

| Event | Description |
|---|---|
| assistant.status | User-facing status such as waiting, generating, completed, failed, or cancelled |
| assistant.summary | Concise, user-facing context or progress summary; never private chain-of-thought |
| agent.started | Agent began work |
| agent.planning | Agent is planning |
| agent.delegated | Task delegated to agent |
| agent.completed | Agent finished |
| task.created | Task created |
| task.started | Task started |
| task.completed | Task completed |
| task.blocked | Task blocked |
| tool.called | Tool invoked |
| tool.failed | Tool failed |
| tool.verified | Tool result verified |
| mcp.connected | MCP server connected |
| mcp.disconnected | MCP server disconnected |
| computer.action_started | Computer action started |
| computer.action_verified | Computer action verified |
| memory.created | Memory stored |
| conversation.followup_detected | Follow-up topic detected |
| approval.requested | User approval needed |
| approval.granted | Approval granted |
| approval.denied | Approval denied |

Each event includes: `event_type`, `timestamp`, `execution_id` (optional), `agent_id` (optional), `data` (event payload). Events are emitted only after authorization and validation; memory events must not imply persistence until the write succeeds.

## 6. Pydantic schemas (draft)

```python
class MessageCreate(BaseModel):
    conversation_id: UUID
    role: Literal["user", "assistant", "system", "tool"]
    content: str
    metadata: Optional[dict] = None

class MessageResponse(BaseModel):
    id: UUID
    conversation_id: UUID
    role: str
    content: str
    created_at: datetime

class TaskCreate(BaseModel):
    execution_id: UUID
    title: str
    description: Optional[str] = None
    expected_result: Optional[str] = None
    required_tools: Optional[list[str]] = None

class TaskResponse(BaseModel):
    id: UUID
    execution_id: UUID
    title: str
    status: str
    created_at: datetime
    updated_at: datetime

class ExecutionResponse(BaseModel):
    id: UUID
    agent_id: UUID
    user_objective: str
    status: str
    current_task: Optional[str]
    completed_tasks: list[UUID]
    pending_tasks: list[UUID]
    created_at: datetime
    updated_at: datetime
```

## 7. Versioning

- API version in URL path (`/api/v1`).
- Breaking changes increment the major version.
- Deprecation notice given at least one release in advance.

## 8. Documentation

- Auto-generated OpenAPI/Swagger at `/docs` and `/openapi.json` (development only, restricted in production).
- Redoc at `/redoc`.
