from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BUILD_ROOT = ROOT / "tools" / "packaging" / "build"
DIST_ROOT = BUILD_ROOT / "dist"
WORK_ROOT = BUILD_ROOT / "work"
RESOURCE_ROOT = ROOT / "desktop" / "src-tauri" / "resources" / "backend"


def run(*args: str) -> None:
    subprocess.run(args, cwd=ROOT, check=True)


def remove_repo_build_dir(path: Path) -> None:
    resolved = path.resolve()
    if ROOT not in resolved.parents:
        raise RuntimeError(f"Refusing to remove path outside repository: {resolved}")
    shutil.rmtree(resolved, ignore_errors=True)


def main() -> None:
    uv = shutil.which("uv")
    if uv is None:
        candidate = Path.home() / ".local" / "bin" / ("uv.exe" if sys.platform == "win32" else "uv")
        if not candidate.is_file():
            raise SystemExit("uv is required; install it using the repository setup instructions")
        uv = str(candidate)

    run(uv, "sync", "--frozen", "--package", "writestory-be", "--group", "build")
    remove_repo_build_dir(BUILD_ROOT)
    remove_repo_build_dir(RESOURCE_ROOT)
    run(
        uv,
        "run",
        "--frozen",
        "--package",
        "writestory-be",
        "--group",
        "build",
        "pyinstaller",
        "--clean",
        "--noconfirm",
        "--distpath",
        str(DIST_ROOT),
        "--workpath",
        str(WORK_ROOT),
        str(ROOT / "tools" / "packaging" / "backend.spec"),
    )
    built = DIST_ROOT / "writestory-backend"
    windows_executable = (built / "writestory-backend.exe").is_file()
    unix_executable = (built / "writestory-backend").is_file()
    if not windows_executable and not unix_executable:
        raise SystemExit(f"PyInstaller output is missing executable: {built}")
    RESOURCE_ROOT.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(built, RESOURCE_ROOT)
    print(f"Backend bundle copied to {RESOURCE_ROOT}")


if __name__ == "__main__":
    main()
