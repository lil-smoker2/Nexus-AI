# Filesystem MCP

**Domain:** Local filesystem operations for NEXUS AI agents (coding, computer, companion/life-management when authorized).  
**Trust boundary:** Every filesystem action must be permission-checked, path-scoped, and auditable. Treat paths and file contents from untrusted sources as untrusted input.

## 1. Purpose and scope

The Filesystem MCP exposes controlled file and directory operations so agents can inspect and modify workspaces without bypassing the permission system.

**In scope (examples):** create, read, write/edit, delete, copy, move/rename, list, search, metadata/stat, path validation.  
**Out of scope:** arbitrary system-wide access outside allowed roots, credential/secret exfiltration, bypassing approvals for destructive actions.

## 2. Prerequisites

- NEXUS backend running with MCP client manager and permission/audit services available.
- A defined allowed root/workspace (e.g. project directory or user-selected folder). Never default to `/` or home-wide access without explicit policy.
- Runtime for the server implementation (choose one):
  - **Node.js** (e.g. reuse `@modelcontextprotocol/server-filesystem` or custom server), or
  - **Python** (custom MCP server using an MCP SDK), or
  - Internal service exposed via MCP wrapper.
- Server registered in MCP registry/config with transport, args/env, and tool permissions.

## 3. How to create the Filesystem MCP (step by step)

### Step 1 — Define scope, roots, and permissions
1. Choose allowed root paths (workspace-only by default).
2. Decide per-tool permissions: `read`, `list`, `search`, `write`, `create`, `delete`, `move`, `copy`.
3. Mark destructive operations (`delete`, overwrite `write`, `move`) as approval-gated where policy requires.
4. Define limits: max file size, max search results, timeout, denied patterns (e.g. `.env`, keys) as applicable.

### Step 2 — Choose transport and create server scaffold
1. Pick transport:
   - `stdio` for local managed process (common for filesystem servers).
   - `streamable_http` for remote/managed service.
2. Create a server project/process entrypoint, e.g.:
   - Node: `npx -y @modelcontextprotocol/server-filesystem <allowed-root>`
   - Custom: implement MCP server with `initialize`, capability negotiation, and tool handlers.
3. Ensure the process runs with least privilege and only the intended working directory/root access.

### Step 3 — Implement MCP handshake and capability discovery
1. Handle MCP `initialize` request/response and negotiate protocol/capabilities.
2. Advertise `tools` capability (and `resources` if used).
3. Implement `tools/list` to return each tool with stable `name`, `description`, and JSON Schema `inputSchema` (and output contract where supported).
4. (Optional) Implement `resources/list` for browsable roots/files if exposed as resources.

### Step 4 — Implement file operation tools (handlers)
Implement each operation as a separate tool with strict validation:

1. **Normalize and validate paths**
   - Resolve absolute/real paths; reject traversal (`..`) escaping allowed roots.
   - Enforce allowlist/denylist and size/type constraints.
2. **Check permissions** (orchestrator/client policy + server-side guard).
3. **Perform operation** using safe APIs.
4. **Return structured result** (success, path(s), metadata, bytes/counts) and actionable errors.
5. **Record/audit** via backend logging (tool call, args summary without secrets, result, duration, verification).

### Step 5 — Add verification and safety behavior
1. After mutating ops, verify outcome (exists/not-exists, size/mtime/hash or expected content where cheap).
2. For copy/move requiring spec/state transfer, verify destination and report “specs moved” state as applicable to product flow.
3. Fail closed on permission/validation errors; never partially claim success.

### Step 6 — Register the MCP in NEXUS
1. Add server entry to MCP registry/config (DB or config file), for example:
```json
{
  "id": "filesystem-local",
  "name": "Local Filesystem",
  "transport": "stdio",
  "endpoint": "npx",
  "args": ["-y", "@modelcontextprotocol/server-filesystem", "/home/david/Documents/AI"],
  "env": {},
  "permissions": ["read", "list", "search", "create", "write", "copy", "move", "delete"],
  "timeout_ms": 30000
}
```
2. Mark trusted/approved per policy; store credentials separately if any.
3. Connect via MCP client manager and confirm `connected` state.

### Step 7 — Test before exposing to agents
1. Test initialize + `tools/list` discovery and schema validity.
2. Test each tool success path and expected failures (missing file, denied path, permission denied, timeout).
3. Test disconnection/reconnection and audit logging.
4. Run with least permissions first, then expand allowlist as needed.

## 4. Tool catalog — file and directory operations

> Tool names may vary by implementation; keep stable IDs in config/permissions. Schemas below are illustrative.

### 4.1 Create
| Tool | Purpose | Key inputs | Notes |
|---|---|---|---|
| `fs.create_file` | Create a new file | `path`, `content?`, `overwrite?` | Fail or require approval if exists unless `overwrite` allowed. Verify file exists after write. |
| `fs.create_directory` | Create directory/folders | `path`, `recursive?` | Idempotent if `recursive` and exists-as-dir; verify directory exists. |

**Example — create file**
```json
{ "name": "fs.create_file", "arguments": { "path": "notes/todo.md", "content": "# TODO\n", "overwrite": false } }
```

### 4.2 Read
| Tool | Purpose | Key inputs | Notes |
|---|---|---|---|
| `fs.read_file` | Read file contents | `path`, `encoding?`, `offset?`, `limit?` | Enforce size limits; return truncated marker when applicable. |
| `fs.read_many_files` (optional) | Batch read | `paths[]` | Bound count/size. |

### 4.3 Write / Edit
| Tool | Purpose | Key inputs | Notes |
|---|---|---|---|
| `fs.write_file` | Write/replace content | `path`, `content`, `create_if_missing?` | Approval-gated for overwrite in sensitive contexts; verify bytes/hash/mtime. |
| `fs.append_file` | Append content | `path`, `content` | Verify growth/content as needed. |
| `fs.edit_file` / `fs.patch` | Targeted edit | `path`, `edits|patch` | Prefer structured edits; verify resulting content when possible. |

### 4.4 Delete
| Tool | Purpose | Key inputs | Notes |
|---|---|---|---|
| `fs.delete_file` | Delete a file | `path` | **Destructive:** require explicit permission/approval per policy; verify file no longer exists. |
| `fs.delete_directory` | Delete directory | `path`, `recursive?` | **High risk:** typically approval-gated; require `recursive` for non-empty; verify removal. |

**Example — delete file**
```json
{ "name": "fs.delete_file", "arguments": { "path": "notes/old.md" } }
```

### 4.5 Copy
| Tool | Purpose | Key inputs | Notes |
|---|---|---|---|
| `fs.copy_file` | Copy file | `source`, `destination`, `overwrite?` | Verify both source and destination exist; preserve/report metadata as needed. |
| `fs.copy_directory` | Copy directory tree | `source`, `destination`, `recursive?` | Verify destination tree; respect limits. |

**Post-copy spec/state note:** when a workflow requires specs/state to move from original to copied artifact, perform/record that transfer explicitly and verify destination reflects moved specs (do not assume copy implies move).

### 4.6 Move / Rename
| Tool | Purpose | Key inputs | Notes |
|---|---|---|---|
| `fs.move_path` / `fs.rename_path` | Move or rename file/dir | `source`, `destination`, `overwrite?` | Verify source absent (or expected) and destination present; handle cross-device moves if supported. |

### 4.7 List and Search
| Tool | Purpose | Key inputs | Notes |
|---|---|---|---|
| `fs.list_directory` | List entries | `path`, `recursive?`, `depth?`, `include_hidden?` | Return name/type/size/mtime; bound result size. |
| `fs.search_files` / `fs.glob` | Find by pattern/name | `root`, `pattern|query`, `max_results?` | Sandbox to root; bound results/time. |
| `fs.search_content` (optional) | Grep-like search | `root`, `query`, `globs?` | Bound matches; treat content as data. |

### 4.8 Metadata and checks
| Tool | Purpose | Key inputs | Notes |
|---|---|---|---|
| `fs.stat` / `fs.get_metadata` | File/dir metadata | `path` | Return exists/type/size/mtime/permissions (as safe). |
| `fs.exists` | Existence check | `path` | Lightweight precondition/check. |

## 5. Suggested JSON Schemas (illustrative)

```json
{
  "name": "fs.create_file",
  "description": "Create a file at an allowed path",
  "inputSchema": {
    "type": "object",
    "properties": {
      "path": { "type": "string", "description": "Path relative to allowed root or approved absolute path" },
      "content": { "type": "string", "default": "" },
      "overwrite": { "type": "boolean", "default": false }
    },
    "required": ["path"]
  }
}
```

```json
{
  "name": "fs.delete_file",
  "description": "Delete a file at an allowed path (destructive)",
  "inputSchema": {
    "type": "object",
    "properties": { "path": { "type": "string" } },
    "required": ["path"]
  }
}
```

## 6. Security and verification checklist

- [ ] All paths resolved and confined to allowed roots (no traversal/symlink escape as per policy).
- [ ] Per-tool permissions enforced; destructive ops approval-gated per policy.
- [ ] Size/time/result limits applied; sensitive paths denied/redacted in logs.
- [ ] Mutations verified (create/write/copy/move/delete outcomes confirmed).
- [ ] Errors returned with safe, actionable messages (no secret leakage).
- [ ] Tool calls and outcomes audited.

## 7. Example end-to-end flow (create → copy → delete)

1. **Create:** `fs.create_file` `{path:"draft/spec.md", content:"..."}` → verify exists.
2. **Copy:** `fs.copy_file` `{source:"draft/spec.md", destination:"final/spec.md"}` → verify both exist; if workflow requires, move/record specs to destination and verify.
3. **Delete:** `fs.delete_file` `{path:"draft/spec.md"}` (with approval if required) → verify source removed.

This pattern supports UI flows that show original vs copied files and spec-movement verification before marking complete.
