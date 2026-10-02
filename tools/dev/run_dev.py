"""Run the local backend and Vite frontend together with prefixed logs."""

from __future__ import annotations

import os
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STOP = threading.Event()


def uv_command() -> str:
    executable = shutil.which("uv")
    if executable:
        return executable
    local_executable = Path.home() / ".local" / "bin" / ("uv.exe" if os.name == "nt" else "uv")
    if local_executable.is_file():
        return str(local_executable)
    raise FileNotFoundError("uv was not found on PATH or in ~/.local/bin")


def pump_output(name: str, process: subprocess.Popen[str]) -> None:
    assert process.stdout is not None
    for line in process.stdout:
        print(f"[{name}] {line.rstrip()}", flush=True)


def start_process(command: list[str], *, cwd: Path = ROOT) -> subprocess.Popen[str]:
    windows = os.name == "nt"
    environment = os.environ.copy()
    environment.setdefault(
        "UV_CACHE_DIR", str(Path(tempfile.gettempdir()) / "writestoryapp-uv-cache")
    )
    environment.setdefault(
        "UV_PYTHON_INSTALL_DIR",
        str(Path.home() / ".local" / "share" / "uv" / "python"),
    )
    return subprocess.Popen(
        command,
        cwd=cwd,
        env=environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
        shell=False,
        start_new_session=not windows,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if windows else 0,
    )


def stop_process(process: subprocess.Popen[str]) -> None:
    if process.poll() is not None:
        return
    try:
        if os.name == "nt":
            process.send_signal(signal.CTRL_BREAK_EVENT)
        else:
            os.killpg(process.pid, signal.SIGTERM)
    except OSError, ProcessLookupError, ValueError:
        process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()


def request_stop(_signum: int, _frame: object) -> None:
    STOP.set()


def main() -> int:
    signal.signal(signal.SIGINT, request_stop)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, request_stop)

    processes: dict[str, subprocess.Popen[str]] = {}
    readers: list[threading.Thread] = []
    exit_code = 0
    try:
        processes["be"] = start_process(
            [uv_command(), "run", "--no-sync", "python", "-m", "writestory_be", "--dev"]
        )
        node = shutil.which("node")
        vite_cli = ROOT / "fe" / "node_modules" / "vite" / "bin" / "vite.js"
        if not node or not vite_cli.is_file():
            raise FileNotFoundError("Node.js or the installed Vite CLI was not found")
        processes["fe"] = start_process([node, str(vite_cli)], cwd=ROOT / "fe")
        readers = [
            threading.Thread(target=pump_output, args=(name, process), daemon=True)
            for name, process in processes.items()
        ]
        for reader in readers:
            reader.start()

        print("[dev] FE: http://localhost:5173/#/system", flush=True)
        while not STOP.wait(0.2):
            failed = next(
                (
                    (name, process.returncode)
                    for name, process in processes.items()
                    if process.poll() is not None
                ),
                None,
            )
            if failed:
                name, process_code = failed
                print(
                    f"[dev] {name} exited with code {process_code}; stopping the other service.",
                    flush=True,
                )
                exit_code = process_code or 0
                break
    except KeyboardInterrupt:
        STOP.set()
    except (OSError, subprocess.SubprocessError) as error:
        print(f"[dev] Could not start development services: {error}", file=sys.stderr)
        exit_code = 1
    finally:
        for process in processes.values():
            stop_process(process)
        for reader in readers:
            reader.join(timeout=1)

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
