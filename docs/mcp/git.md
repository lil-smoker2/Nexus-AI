# Git MCP

**Domain:** Repository inspection and controlled Git operations for project-aware workflows.

## 1. Purpose
Expose repository state and safe Git actions (status, diff, log, branches, commits) through MCP with policy controls.

## 2. Prerequisites
- Git installed; repository/workspace path allowed.
- Policy for mutating operations (commit, push, checkout, reset) and identity/config handling.

## 3. How to create the Git MCP
1. **Define scope:** allowed repos/paths, read-only vs mutating tools, protected branches, remote policies.
2. **Scaffold server:** MCP server running in/targeting approved repo context.
3. **Implement tools:**
   - `git.status`, `git.diff` (`staged?`, `pathspec?`)
   - `git.log` (`limit`, `ref?`)
   - `git.show` (`ref`, `path?`)
   - `git.branch_list`, `git.current_branch`
   - `git.add`, `git.commit` (gated; message/author policy)
   - `git.checkout` / `git.switch` (gated)
   - `git.push` / `git.pull` (gated, credential-safe)
4. **Safety:** never expose credentials, require approvals for pushes/destructive ops, prevent unintended repo escape.
5. **Verification:** confirm clean/expected status, commit created, branch state, remote result as applicable.
6. **Register & test:** discovery, read ops, gated write ops, failure modes (conflicts, no remote).

## 4. Operations summary
- **Inspect:** status, diffs, logs, branches, file history.
- **Local changes (gated):** stage/commit/branch operations per policy.
- **Remote sync (gated):** fetch/pull/push with explicit authorization.

## 5. Security checklist
- [ ] Repo paths constrained; no credential leakage
- [ ] Mutating/remote ops permission- and approval-gated
- [ ] Protected branch policies respected
- [ ] Actions and outcomes audited
