# NEXUS AI — Database Design

**Status:** Draft — Phase 0, Step 0.5  
**Source:** NEXUS_AI_Revised_Master_Roadmap.md, PART II Section 4.3

## 1. Database choice

Initial database: **SQLite** (single-file, zero-server, ideal for a desktop application).
- Migration layer: Alembic or equivalent.
- Repository/data-access layer prevents business logic from depending directly on SQLite-specific SQL.
- Optional PostgreSQL for deployments needing concurrent/remote/larger-scale access.
- Optional vector search (pgvector) when semantic retrieval has a tested need — not a prerequisite for first release.

## 2. Design principles

- All database-specific operations are behind the data-access layer (repository pattern).
- Every long-running operation has a persistent execution ID.
- Every important side effect has a verification step recorded.
- Timestamps stored in UTC.
- Soft deletes preferred over hard deletes where user data is involved.
- Foreign keys enforced; cascade rules documented per relationship.

## 3. Entity relationship overview

```text
users (1) ─── (N) conversations
users (1) ─── (N) settings
users (1) ─── (N) memories
users (1) ─── (N) approvals

conversations (1) ─── (N) messages
conversations (1) ─── (N) executions

executions (1) ─── (N) tool_calls
executions (1) ─── (N) checkpoints
executions (1) ─── (N) errors

tasks (1) ─── (N) subtasks
tasks (1) ─── (N) task_dependencies (self-referential)
tasks (1) ─── (N) task_executions

mcp_servers (1) ─── (N) mcp_tools
mcp_servers (1) ─── (N) mcp_connections

agents (1) ─── (N) agent_permissions
agents (1) ─── (N) executions

files (1) ─── (N) file_operations
```

## 4. Core entities

### 4.1 users

| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| username | TEXT unique | |
| created_at | TIMESTAMP UTC | |
| updated_at | TIMESTAMP UTC | |

### 4.2 settings

| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| user_id | UUID FK → users | |
| key | TEXT | e.g. theme, default_model, quiet_hours |
| value | TEXT | JSON-encoded |
| updated_at | TIMESTAMP UTC | |

### 4.3 conversations

| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| user_id | UUID FK → users | |
| title | TEXT | |
| created_at | TIMESTAMP UTC | |
| updated_at | TIMESTAMP UTC | |

### 4.4 messages

| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| conversation_id | UUID FK → conversations | |
| role | TEXT | user / assistant / system / tool |
| content | TEXT | |
| created_at | TIMESTAMP UTC | |
| metadata | JSONB | optional (model, tokens, agent) |

The interface may display message delivery/generation state, but transient UI state should not be persisted as message content. Any user-facing activity summary persisted with an execution must remain separate from hidden model reasoning.

### 4.5 executions (persistent execution state)

| Column | Type | Notes |
|---|---|---|
| id | UUID PK | Execution ID |
| agent_id | UUID FK → agents | |
| user_objective | TEXT | |
| plan_version | INTEGER | |
| current_task | TEXT | |
| status | TEXT | pending / running / completed / blocked / failed |
| completed_tasks | JSON | list of task IDs |
| pending_tasks | JSON | list of task IDs |
| tool_calls | JSON | recorded tool calls |
| tool_results | JSON | recorded tool results |
| errors | JSON | recorded errors |
| checkpoints | JSON | checkpoint records |
| approvals | JSON | permission decisions |
| verification_evidence | JSON | post-action verification |
| final_report | TEXT | completion report |
| created_at | TIMESTAMP UTC | |
| updated_at | TIMESTAMP UTC | |

### 4.6 tasks

| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| execution_id | UUID FK → executions | |
| parent_task_id | UUID FK → tasks | nullable (subtasks) |
| title | TEXT | |
| description | TEXT | |
| expected_result | TEXT | |
| status | TEXT | pending / in_progress / completed / blocked / failed |
| required_tools | JSON | list of tool IDs |
| completion_conditions | JSON | |
| risks | JSON | |
| dependencies | JSON | list of task IDs |
| created_at | TIMESTAMP UTC | |
| updated_at | TIMESTAMP UTC | |

### 4.7 memories

| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| user_id | UUID FK → users | |
| category | TEXT | personal_info / preferences / interests / goals / events / projects / commitments |
| content | TEXT | |
| source | TEXT | where the memory came from |
| embedding | VECTOR | optional, for semantic search |
| importance | INTEGER | |
| created_at | TIMESTAMP UTC | |
| updated_at | TIMESTAMP UTC | |
| expires_at | TIMESTAMP UTC | nullable |

The context panel may surface relevant memory records, but a suggestion or temporary inference is not a memory record until the user-approved persistence flow succeeds. UI state must not create duplicate or implicit memory writes.

### 4.8 mcp_servers

| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| name | TEXT | |
| transport | TEXT | stdio / streamable_http |
| endpoint | TEXT | executable path or URL |
| args | JSON | |
| env | JSON | |
| auth_config | JSON | |
| connection_state | TEXT | connected / disconnected / error |
| permissions | JSON | tool-level allowlist |
| created_at | TIMESTAMP UTC | |
| updated_at | TIMESTAMP UTC | |

### 4.9 approvals

| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| user_id | UUID FK → users | |
| execution_id | UUID FK → executions | nullable |
| tool_id | TEXT | |
| resource | TEXT | |
| decision | TEXT | requested / granted / denied |
| scope | TEXT | narrowly scoped authorization |
| created_at | TIMESTAMP UTC | |
| decided_at | TIMESTAMP UTC | nullable |

### 4.10 agents

| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| name | TEXT | companion / coding / computer / life_management |
| capabilities | JSON | declared capabilities |
| permissions | JSON | assigned permissions |
| created_at | TIMESTAMP UTC | |

## 5. Indexes

- messages(conversation_id, created_at)
- executions(user_id) via agent → user
- tasks(execution_id, status)
- memories(user_id, category)
- mcp_servers(connection_state)
- approvals(execution_id, decision)

## 6. Migrations

- Initial migration creates all core tables.
- Alembic (or equivalent) for versioned migrations.
- Migration tests verify up/down cycles.
- Data survives restart and supported upgrades (backup/restore of SQLite file).

## 7. Data-access layer

Repository interfaces per entity group:
- ConversationRepository, MessageRepository
- ExecutionRepository, TaskRepository
- MemoryRepository
- McpServerRepository, ApprovalRepository
- AgentRepository, SettingsRepository

Business logic depends on interfaces, not SQLite-specific SQL.

## 8. Backup and restore

- Backup: copy the SQLite file + WAL/SHM if present.
- Restore: replace the SQLite file with the backup, re-run migrations if needed.
- Documented in docs/setup-recovery.md.
