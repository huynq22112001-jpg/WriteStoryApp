import asyncio
import logging
import os
import sys
import threading
from pathlib import Path
from typing import IO

log = logging.getLogger(__name__)


class BackendLockError(Exception):
    pass


class BackendLock:
    """Khóa độc quyền `data/db/.backend.lock` (Plan §24 D24): chặn hai backend trên một DB.

    Dùng khóa của hệ điều hành nên tự nhả khi tiến trình chết; không dựa vào "file tồn tại".
    """

    def __init__(self, path: Path) -> None:
        self.path = path
        self._fh: IO[bytes] | None = None

    def acquire(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fh = open(self.path, "a+b")  # noqa: SIM115 – giữ mở suốt vòng đời backend
        try:
            if sys.platform == "win32":
                import msvcrt

                fh.seek(0)
                msvcrt.locking(fh.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            fh.close()
            raise BackendLockError(str(self.path)) from exc
        self._fh = fh

    def release(self) -> None:
        if self._fh is None:
            return
        try:
            if sys.platform == "win32":
                import msvcrt

                self._fh.seek(0)
                msvcrt.locking(self._fh.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl

                fcntl.flock(self._fh.fileno(), fcntl.LOCK_UN)
        finally:
            self._fh.close()
            self._fh = None


class ProtocolChannel:
    """Kênh NDJSON tới Rust trên stdout gốc. `sys.stdout` bị chuyển sang stderr để thư viện
    in lung tung không làm hỏng giao thức (F00 be.md §B.5)."""

    def __init__(self) -> None:
        self._out = os.fdopen(os.dup(sys.stdout.fileno()), "w", encoding="utf-8", buffering=1)
        sys.stdout = sys.stderr
        self._lock = threading.Lock()

    def emit(self, message_json: str) -> None:
        with self._lock:
            self._out.write(message_json + "\n")
            self._out.flush()


def watch_stdin_eof(loop: asyncio.AbstractEventLoop, on_eof) -> threading.Thread:
    """Khi Rust chết hoặc đóng pipe, stdin trả EOF → yêu cầu tắt (Review §7.1 lưới an toàn)."""

    def _run() -> None:
        stream = sys.stdin.buffer
        while True:
            try:
                line = stream.readline()
            except (OSError, ValueError):
                line = b""
            if not line:
                log.info("stdin EOF – yêu cầu tắt backend")
                loop.call_soon_threadsafe(on_eof)
                return

    thread = threading.Thread(target=_run, name="stdin-eof-watcher", daemon=True)
    thread.start()
    return thread
