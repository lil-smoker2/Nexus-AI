# NEXUS AI — Arch Linux Environment Verification

**Status:** Draft — Phase 0, Step 0.3  
**Target:** Arch Linux, GNOME, Wayland

## Verified development tools

Each tool was verified independently by checking its version.

| Tool | Version | Status |
|---|---|---|
| Git | 2.56.0 | Installed |
| Python | 3.14.8 | Installed (`/usr/bin/python3`) |
| pip | 26.2.2 | Installed |
| Python venv module | available | Installed |
| Node.js | v26.12.1 | Installed |
| npm | 12.2.1 | Installed |
| npx | available | Installed |
| Rust / rustc | 1.99.1 | Installed |
| Cargo | 1.99.1 | Installed |
| SQLite / sqlite3 | 3.54.0 | Installed |

## Desktop environment

| Item | Value | Status |
|---|---|---|
| XDG_CURRENT_DESKTOP | GNOME | Confirmed |
| XDG_SESSION_TYPE | wayland | Confirmed |
| GNOME Shell | 51.1 | Confirmed |

## Not yet installed (optional / to install on demand)

| Tool | Reason | Plan |
|---|---|---|
| pnpm | package manager alternative | npm is sufficient; add pnpm later if preferred |
| tauri-cli | Tauri development CLI | Install via `cargo install tauri-cli` when initializing Tauri (Phase 1) |
| psql / PostgreSQL | database server | SQLite is the initial database per architecture; PostgreSQL optional later |

## Notes

- System Python is preserved as-is. A project virtual environment will be created for backend dependencies (see `docs/setup-recovery.md`).
- All Phase 0 required tools are present and verified. No installation was needed.
- The environment matches the initial target platform: Arch Linux with GNOME and Wayland.
