# NEXUS AI — MCP Specs Index

This directory divides MCP integration into per-domain MCP specifications. See [../mcp-integration-spec.md](../mcp-integration-spec.md) for the cross-cutting architecture, client manager, registry, security, and tool contract.

## MCPs

| MCP | Spec | Primary operations |
|---|---|---|
| Filesystem | [filesystem.md](filesystem.md) | Create/read/write/edit/delete/copy/move/rename/list/search/stat files and directories (with step-by-step MCP creation guide) |
| Terminal | [terminal.md](terminal.md) | Execute commands, inspect output/processes, controlled termination |
| Browser | [browser.md](browser.md) | Sessions, navigation, DOM inspection, interaction, downloads |
| Database | [database.md](database.md) | Connection/schema inspection, permitted queries |
| Git | [git.md](git.md) | Status/diff/log/branch and gated mutating/remote ops |
| Computer Automation | [computer-automation.md](computer-automation.md) | Desktop/window/app inspection and gated UI automation |
| Task and Memory | [task-memory.md](task-memory.md) | Task/TODO persistence and memory store/retrieve/manage |
