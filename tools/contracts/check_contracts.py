"""Regenerate OpenAPI contracts and fail when committed artifacts drift."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS = (
    ROOT / "contracts" / "openapi.json",
    ROOT / "fe" / "src" / "shared" / "api" / "generated" / "schema.d.ts",
)


def run(command: list[str]) -> None:
    if command[0] == "uv" and shutil.which("uv") is None:
        local_uv = Path.home() / ".local" / "bin" / "uv.exe"
        if local_uv.is_file():
            command[0] = str(local_uv)
    environment = os.environ.copy()
    environment.setdefault(
        "UV_CACHE_DIR", str(Path(tempfile.gettempdir()) / "writestoryapp-uv-cache")
    )
    environment.setdefault(
        "UV_PYTHON_INSTALL_DIR",
        str(Path.home() / ".local" / "share" / "uv" / "python"),
    )
    subprocess.run(
        subprocess.list2cmdline(command) if sys.platform == "win32" else command,
        cwd=ROOT,
        env=environment,
        check=True,
        shell=sys.platform == "win32",
    )


def main() -> int:
    before = {path: path.read_bytes() if path.exists() else None for path in ARTIFACTS}
    run(["uv", "run", "--no-sync", "python", "tools/contracts/export_openapi.py"])
    run(["pnpm", "--filter", "fe", "gen:api"])

    changed = [
        path.relative_to(ROOT).as_posix() for path in ARTIFACTS if before[path] != path.read_bytes()
    ]
    if changed:
        print("Contract artifacts are stale; regenerate and review:", file=sys.stderr)
        for path in changed:
            print(f"  - {path}", file=sys.stderr)
        return 1

    print("OpenAPI contract artifacts are up to date.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
