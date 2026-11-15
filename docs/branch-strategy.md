# NEXUS AI — Git Branch Strategy

**Status:** Draft — Phase 0, Step 0.10

## Branches

- `main` — Production-ready, stable code. Only merged changes that pass all acceptance criteria.
- `develop` — Integration branch for completed features. Release candidates branch from here.
- `feature/<name>` — Short-lived feature branches (e.g. `feature/companion-memory`, `feature/file-copy-widget`). Branched from `develop`, merged back via pull request.
- `phase/<N>-<short-name>` — Phase-level work branches (e.g. `phase/0-requirements`, `phase/1-desktop-shell`). Branched from `develop`.
- `hotfix/<name>` — Urgent production fixes. Branched from `main`, merged to both `main` and `develop`.

## Naming conventions

Use lowercase, hyphen-separated, descriptive names:
- `feature/companion-conversational-engine`
- `phase/1-desktop-shell`
- `hotfix/websocket-reconnect`

## Commit conventions

Conventional Commits format:

```
<type>(<scope>): <description>
```

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`, `perf`, `ci`, `build`, `revert`.

Examples:
- `feat(companion): add conversational engine for natural short responses`
- `fix(tools): handle file copy verification failure`
- `docs(roadmap): add weather and time dashboard widgets`
- `test(tools): add file copy verification tests`

Scope should match the module or component being changed.

## Pull request requirements

- Linked to an issue or phase task.
- Passes lint and typecheck.
- Includes tests for new behaviour.
- Updated documentation where relevant.
- UI changes include an updated design reference or a screenshot-based review note where useful, plus accessibility and minimum-window checks.
- At least one approval before merge to `develop` or `main`.

## Workflow

1. Create a feature/phase branch from `develop`.
2. Implement and test.
3. Commit with conventional commit messages.
4. Open a pull request to `develop`.
5. After review and approval, merge.
6. When a phase is complete and acceptance criteria are met, create a release candidate from `develop`, test, then merge to `main` and tag.

## Tags

Use semantic versioning tags (e.g. `v0.1.0`, `v0.2.0`) on `main` at each release milestone.
