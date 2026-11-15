# NEXUS AI — Setup and Recovery Procedures

**Status:** Draft — Phase 0, Step 0.12

## 1. Development environment setup (Arch Linux)

Verify each tool independently before proceeding:

```bash
# Git
git --version

# Python (use a supported interpreter; do not replace system Python)
python3 --version

# Node.js and npm/pnpm
node --version
npm --version

# Rust and Cargo
rustc --version
cargo --version

# SQLite tooling
sqlite3 --version
```

### Python virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
```

### Node / Tauri

```bash
# Install Tauri CLI (via cargo)
cargo install tauri-cli
```

## 2. Project setup

```bash
# Clone the repository
git clone <repo-url> nexus-ai
cd nexus-ai

# Python backend
source .venv/bin/activate
pip install -r backend/requirements.txt   # when created

# Frontend
cd desktop
npm install                                # or pnpm install
cd ..
```

## 3. Running the application

### Development mode

Start the backend (FastAPI) and the Tauri frontend in development mode. The Tauri shell manages the backend lifecycle.

Use the SVG in [docs/chat-experience.md](./chat-experience.md) as the visual reference when validating the companion chat workspace. It is a design preview, not a live application screenshot.

### Production build

```bash
# Frontend production build
cd desktop && npm run build && cd ..

# Tauri production package
cargo tauri build
```

## 4. Database

Initial database is SQLite. Migrations managed via Alembic or equivalent.

```bash
# Apply migrations
alembic upgrade head
```

Backup: copy the SQLite file. Restore: replace the SQLite file with the backup.

## 5. Recovery procedures

### Backend crash

The Tauri shell detects backend non-readiness and attempts restart. Check backend logs for the cause.

### Corrupted execution state

Executions are persisted in the database. An interrupted task can be resumed from its last checkpoint by loading the execution record and reconstructing state.

### Lost frontend state

Frontend state is rebuilt from backend data via API/WebSocket on reconnect. Conversations and tasks survive restart because they are persisted.

### Dependency failure

If a library does not support the installed Python version, use a separate supported interpreter in a dedicated virtual environment rather than replacing the system Python.

## 6. What to verify after setup

- Backend health-check endpoint responds.
- Frontend can reach the backend.
- WebSocket connection opens.
- Backend shutdown does not leave orphan processes.
- Application launches and closes cleanly.
- The companion chat remains usable at the supported minimum window size, including its composer and collapsible context panel.
