# Database MCP

**Domain:** Controlled database connectivity, schema inspection, and permitted query execution.

## 1. Purpose
Enable agents to inspect schemas and run approved queries against configured databases without exposing raw credentials broadly.

## 2. Prerequisites
- Database driver(s) for supported engines (SQLite/PostgreSQL/etc.).
- Connection profiles stored securely; least-privilege DB credentials.

## 3. How to create the Database MCP
1. **Define scope:** allowed connections, read-only vs read-write, statement classes, row/time limits.
2. **Scaffold server:** MCP server with secure config loading (no secrets in logs).
3. **Implement tools:**
   - `db.list_connections` (metadata only)
   - `db.inspect_schema` (`connection`, tables/columns/indexes)
   - `db.execute_query` (`connection`, `query`, `params?`, `limit?`) — prefer parameterized; enforce policy (e.g. read-only by default).
   - `db.explain` (optional) — query plan where supported.
4. **Safety:** block destructive statements unless explicitly approved, enforce timeouts/row caps, redact sensitive values.
5. **Verification:** return row counts/affected rows and schema-consistent results; validate against expectations when applicable.
6. **Register & test:** discovery, schema inspection, safe queries, denied queries, timeout handling.

## 4. Operations summary
- **Connect/inspect:** list approved connections, inspect schemas.
- **Query:** execute permitted parameterized queries with bounded results.
- **Admin (gated):** migrations/writes only with explicit permission and approval.

## 5. Security checklist
- [ ] Credentials isolated and never logged
- [ ] Read/write policies enforced per connection
- [ ] Query limits/timeouts applied
- [ ] Results audited and sensitive data handled per policy
