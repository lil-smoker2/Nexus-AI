# NEXUS AI — Linting, Formatting and Testing Conventions

**Status:** Draft — Phase 0, Step 0.11

## Python (backend)

### Formatting
- `black` with line length 88.
- `isort` for import ordering.

### Linting
- `flake8` or `ruff` for linting.
- `mypy` for static type checking (strict where practical).

### Testing
- `pytest` for unit and integration tests.
- Tests located in `backend/tests/` mirroring the source structure.
- Test naming: `test_<module>.py` for modules, `test_<function>_<scenario>` for cases.
- Fixtures in `conftest.py`.
- Coverage target: aim for meaningful coverage of business logic; 100% is not required but critical paths (tools, permissions, execution, orchestrator) should be well covered.

### Commands (suggested)
```
black backend/
isort backend/
ruff check backend/
mypy backend/
pytest backend/tests/
```

## TypeScript / React (frontend)

### Formatting
- `prettier` with default settings.

### Linting
- `eslint` with TypeScript plugin.
- `tsc --noEmit` for type checking.

### Testing
- Vitest or Jest for unit and component tests.
- React Testing Library for component tests.
- Playwright for end-to-end desktop UI tests.
- Tests located alongside source (`*.test.ts`, `*.test.tsx`) or in `__tests__/`.

### Commands (suggested)
```
prettier --write "desktop/src/**/*.{ts,tsx,css}"
eslint "desktop/src/**/*.{ts,tsx}"
tsc --noEmit
vitest run
```

## Tauri / Rust

### Formatting
- `cargo fmt`.

### Linting
- `cargo clippy`.

### Testing
- `cargo test`.

### Commands (suggested)
```
cargo fmt
cargo clippy
cargo test
```

## General rules

- Run lint, typecheck and tests before every commit.
- CI should run lint, typecheck and tests on pull requests.
- No committing broken builds.
- Document new public APIs and behaviours.
- Security-sensitive code (permissions, credentials, tool execution) requires review and tests.
