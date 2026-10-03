# ADR-002: Backend onedir trong resources Tauri

- Status: accepted for the Windows R0 bundle; clean-machine validation remains open.
- Date: 2026-10-03.
- Context: production startup must not depend on Python or uv being installed. The backend needs writable data and log paths and must stop with the desktop process.

## Decision

Package the PyInstaller onedir output under `resources/backend/`. In Tauri release builds Rust starts `resource_dir/backend/writestory-backend[.exe]` directly, sends one `BootstrapConfig` line on stdin, and validates the `ready` protocol plus health response. Debug builds continue to use `uv run python -m writestory_be`. Alembic config/migrations and AI language data are bundled with the executable.

## Windows build evidence (2026-10-03)

- `uv run --package writestory-be --group build python tools/packaging/build_backend.py`: completed; PyInstaller 6.22.3, Windows 11 x64, Python 3.14.8.
- Direct packaged backend smoke: migrations completed and stdout emitted `{"event":"ready", ...}` with an OS-assigned loopback port.
- Bundled backend directory: 54,706,625 bytes (52.17 MiB).
- NSIS offlineInstaller artifact built successfully: 241,288,169 bytes (230.11 MiB).
- Raw release executable with bundled resources: first launch-to-ready 6.74 s; subsequent launch-to-ready 1.56 s. One sample each, on this Windows 11 x64 development host, not a clean-machine benchmark.
- After 5 seconds at ready: app working set 26.6 MiB, backend working set 110.9 MiB (137.5 MiB combined). One sample, not a long-duration idle profile.
- Installer installation and launch on a clean machine without Python/uv: not performed; current host is not a clean machine.

## Operations

Run `uv run --package writestory-be --group build python tools/packaging/build_backend.py` before `tauri build`. The build script synchronizes the locked build group, creates a PyInstaller onedir bundle, and copies it to `desktop/src-tauri/resources/backend/`. Release startup expects that directory to be present. On macOS, sign each Mach-O in the resource bundle before building the app.
