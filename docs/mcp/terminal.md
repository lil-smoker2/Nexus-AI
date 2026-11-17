# Terminal MCP

**Domain:** Controlled command execution, process inspection, and terminal output retrieval for NEXUS AI agents.

## 1. Purpose
Expose shell/command capabilities through MCP with strict permissioning, timeouts, and auditability (used heavily by coding/computer agents).

## 2. Prerequisites
- Allowed working directories and command policy (allowlist/denylist) defined.
- Runtime environment (Python/Node) and PTY/exec backend as needed.
- Resource limits: timeout, output size, concurrency.

## 3. How to create the Terminal MCP
1. **Define policy:** allowed cwd roots, allowed/blocked commands, env handling, network/privilege constraints.
2. **Scaffold server:** stdio or streamable_http MCP server with `initialize` and `tools/list`.
3. **Implement tools:**
   - `terminal.execute` — run command (`command`, `args[]` or `shell` flag per policy, `cwd`, `env?`, `timeout_ms`) returning `exit_code`, `stdout`, `stderr`, `duration`.
   - `terminal.get_output` / streaming (optional) — fetch buffered/ongoing output by exec id.
   - `terminal.list_processes` (optional) — inspect managed/allowed processes.
   - `terminal.kill_process` (optional, gated) — terminate managed process.
4. **Safety controls:** block interactive shells by default unless supported, redact secrets in logs, enforce cwd sandbox, kill on timeout.
5. **Verification:** confirm exit code/output, detect failures, capture artifacts needed for debugging.
6. **Register & test:** add to MCP registry, test success/failure/timeout/denied-command cases and reconnection.

## 4. Operations summary
- **Execute:** run build/test/lint/dev commands in approved cwd.
- **Inspect:** read status/output, list processes.
- **Control:** cancel/kill managed runs (approval-gated if destructive).

## 5. Security checklist
- [ ] Command/cwd allowlisted and validated
- [ ] Timeouts and output caps enforced
- [ ] Secrets not echoed/logged
- [ ] All executions audited with exit status
