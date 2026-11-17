# Task and Memory MCP

**Domain:** Persistent task/TODO management and memory operations exposed to agents via MCP.

## 1. Purpose
Allow agents to create/track tasks and store/retrieve relevant memories through a controlled, auditable interface backed by NEXUS persistence.

## 2. Prerequisites
- Database/persistence layer and repositories available.
- Memory/task schemas, retention, and visibility/ownership rules defined.

## 3. How to create the Task and Memory MCP
1. **Define scope:** which agents/users can read/write which records, memory categories, retention and redaction rules.
2. **Scaffold server:** MCP server (or internal wrapper) that calls backend services/repositories rather than duplicating core logic.
3. **Implement task tools:**
   - `task.create`, `task.update`, `task.list`, `task.get`
   - `task.add_subtask`, `task.set_status`, `task.record_blocker`
   - Link tasks to executions/conversations where applicable.
4. **Implement memory tools:**
   - `memory.store` (type/category, content, source, confidence/metadata)
   - `memory.search` / `memory.retrieve` (scoped queries)
   - `memory.update`, `memory.delete` (user/agent-permitted corrections)
5. **Safety:** enforce ownership/visibility, avoid storing secrets, validate schemas, support user correction/deletion.
6. **Verification:** confirm records persisted/updated and queries return expected scoped results.
7. **Register & test:** CRUD/search flows, permission boundaries, deletion/retention behavior.

## 4. Operations summary
- **Tasks:** create, plan, update status, track blockers and completion.
- **Memory:** store, retrieve/search, correct, and delete scoped memories.

## 5. Security checklist
- [ ] Access scoped by user/agent/context
- [ ] Sensitive data excluded or protected
- [ ] Mutations audited with provenance
- [ ] User correction/deletion supported
