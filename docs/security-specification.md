# NEXUS AI — Security Specification

**Status:** Draft — Phase 0, Step 0.5  
**Source:** NEXUS_AI_Revised_Master_Roadmap.md, PART II Section 11; PART V Sections 11–12

## 1. Security principles

- **Least privilege:** Agents only have the capabilities they need.
- **No unrestricted root:** No model executes arbitrary sudo commands without controlled authorization.
- **Approval for risky operations:** Destructive, privileged, financial, credential-sensitive or externally consequential operations require user confirmation.
- **Audit everything:** Authorization decisions, tool calls, permission changes are logged.
- **Credentials never exposed:** Secrets not in logs or model prompts.
- **Untrusted content:** Website content, documents, emails, screenshots, terminal output, downloads and external MCP responses treated as untrusted input.
- **Prompt injection protection:** External content cannot override system policy or grant itself permissions.

## 2. Permission categories

| Permission | Example | Risk level |
|---|---|---|
| Read | Read an authorized document | Low |
| Write | Create a new document | Low |
| Modify | Edit an existing project file | Medium |
| Delete | Delete a file | High |
| Execute | Run a command | High |
| Install | Install software | High |
| Network | Access an external website | Medium |
| Credentials | Use a stored credential | High |
| Financial | Make a purchase or payment | Critical |
| Administrative | Perform privileged system operations | Critical |

## 3. Permission model

Permissions defined by:
- **Agent** — which agent may use the tool
- **Tool** — specific tool identifier
- **Resource** — specific file, directory, URL, process
- **Session** — time-bound, narrowly scoped authorization

Session-based approvals for harmless, reversible operations within user-approved scopes. No permission asked on every harmless operation.

## 4. Approval flow

```
Tool request → Permission check → Allowed scope?
  No → Reject (unauthorized)
  Yes → Risky operation?
    No → Execute with audit log
    Yes → Request user approval (narrowly scoped)
      Granted → Execute with audit log
      Denied → Reject (approval denied)
```

## 5. Credential protection

- Secrets stored in secure storage (OS keyring or encrypted file).
- Never logged, never sent to model prompts, never displayed in UI.
- Credential configuration UI shows masked values only.
- Credential access requires explicit permission.

## 6. MCP server isolation

- Each external MCP server is a separate trust boundary.
- Server allowlisting — only approved servers connect.
- Tool-level allowlists — only approved tools usable.
- Server health monitoring — track errors and disconnects.
- Output validation — validate against schema before agent use.

## 7. Filesystem restrictions

- Allowed directory restrictions — agents operate within authorized directories only.
- Path traversal prevention.
- File-size limits.
- Protection of sensitive locations (system files, SSH keys, credentials).
- File deletion requires explicit approval.

## 8. Process isolation

- Command validation — block dangerous commands.
- Dangerous operation detection (rm -rf, format, mkfs, etc.).
- Execution timeouts.
- Output size limits.
- Process termination capability.
- Application launching/termination within approved scope.

## 9. Network restrictions

- Domain restrictions where configured.
- Download restrictions (file types, size, destination).
- Session isolation for browser automation.
- No automatic access to external websites without user consent.

## 10. Prompt injection protection

Content from these sources is treated as untrusted:
- Websites
- Documents
- Emails
- MCP servers
- Application screens
- Downloaded files

Such content may inform a task but must not:
- Override system policies
- Grant itself permissions
- Expose secrets
- Authorize unrelated actions

## 11. Audit logging

Record:
- Agent decisions and selected actions
- Tool calls and results
- Execution duration
- Errors and retries
- Model usage and token consumption
- MCP connection events
- Permission decisions (granted/denied)
- Approval requests and outcomes

Audit logs are append-only and tamper-evident where possible.

## 12. Security testing

| Test | Description |
|---|---|
| Unauthorized actions blocked | Verify agents cannot execute without permission |
| Sensitive action approval | Verify approval flow for delete/execute/install |
| Auditable permissions | Verify all permission decisions logged |
| Credential secrecy | Verify secrets not in logs or prompts |
| Least privilege per agent | Verify each agent has only needed capabilities |
| MCP server isolation | Verify untrusted servers cannot access unauthorized tools |
| Prompt injection | Verify external content cannot change policy |

## 13. Security by phase

Security is not postponed to the final phase. Permission management is established in Phase 5 (before tools), with ongoing hardening in Phase 17 (production hardening).
