"""Điểm vào backend (F00 be.md §B).

- Chế độ desktop (mặc định): đọc một dòng `BootstrapConfig` từ stdin, bind cổng do OS cấp,
  in `ready` qua kênh protocol, tắt khi stdin EOF hoặc nhận `POST /v1/system/shutdown`.
- Chế độ `--dev`: cấu hình từ biến môi trường, cổng cố định cho Vite dev server (S06).
"""

import argparse
import asyncio
import logging
import os
import socket
import sys
from pathlib import Path

import uvicorn
from pydantic import ValidationError

from writestory_be.bootstrap.context import Runtime, prepare_data_root
from writestory_be.bootstrap.lifecycle import (
    BackendLock,
    BackendLockError,
    ProtocolChannel,
    watch_stdin_eof,
)
from writestory_be.bootstrap.logging_setup import configure_logging
from writestory_be.bootstrap.protocol import (
    BACKEND_PROTOCOL_VERSION,
    BootstrapConfig,
    FatalMessage,
    ProgressMessage,
    ProtocolMismatchError,
    ReadyMessage,
    parse_bootstrap_line,
)
from writestory_be.main import create_app

log = logging.getLogger(__name__)

EXIT_PROTOCOL = 3
EXIT_STARTUP = 4

DEV_PORT = 8765
DEV_TOKEN = "dev-token"
DEV_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173"]


def dev_config() -> BootstrapConfig:
    data_root = Path(os.environ.get("WRITESTORY_DATA_ROOT", Path.cwd() / "data")).resolve()
    return BootstrapConfig(
        protocol_version=BACKEND_PROTOCOL_VERSION,
        token=os.environ.get("WRITESTORY_DEV_TOKEN", DEV_TOKEN),
        data_root=data_root,
        data_id="dev",
        allowed_origins=DEV_ORIGINS,
        dev_features=True,
        log_level="debug" if os.environ.get("WRITESTORY_DEBUG") else "info",
        port=int(os.environ.get("WRITESTORY_DEV_PORT", DEV_PORT)),
    )


def bind_socket(host: str, port: int) -> socket.socket:
    """Bind trước rồi trao socket cho uvicorn để tránh tranh chấp cổng (Plan §3 bước 4)."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    if sys.platform != "win32":
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((host, port))
    sock.listen(128)
    sock.set_inheritable(False)
    return sock


async def serve(runtime: Runtime, sock: socket.socket, emit_ready) -> None:
    app = create_app(runtime)
    config = uvicorn.Config(
        app,
        lifespan="on",
        log_config=None,
        access_log=False,
        timeout_graceful_shutdown=5,
    )
    server = uvicorn.Server(config)
    runtime.server = server

    async def announce_ready() -> None:
        while not server.started:
            if server.should_exit:
                return
            await asyncio.sleep(0.02)
        emit_ready()

    announcer = asyncio.create_task(announce_ready())
    try:
        await server.serve(sockets=[sock])
    finally:
        announcer.cancel()


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="writestory-backend")
    parser.add_argument("--dev", action="store_true", help="Chạy dev: cổng cố định, token dev")
    args = parser.parse_args(argv)

    channel = ProtocolChannel()

    def fatal(code: str, message: str, **detail) -> None:
        channel.emit(FatalMessage(code=code, message=message, detail=detail).model_dump_json())

    if args.dev:
        config = dev_config()
    else:
        # Đọc qua buffer nhị phân, cùng lớp với luồng theo dõi EOF (lifecycle.watch_stdin_eof).
        line = sys.stdin.buffer.readline().decode("utf-8")
        try:
            config = parse_bootstrap_line(line)
        except ProtocolMismatchError as exc:
            fatal("PROTOCOL_MISMATCH", str(exc), expected=BACKEND_PROTOCOL_VERSION)
            return EXIT_PROTOCOL
        except ValidationError as exc:
            fatal("BOOTSTRAP_INVALID", "BootstrapConfig không hợp lệ", errors=exc.error_count())
            return EXIT_PROTOCOL

    data_root = config.data_root.resolve()
    config = config.model_copy(update={"data_root": data_root})

    try:
        prepare_data_root(data_root)
    except OSError as exc:
        fatal("DATA_ROOT_UNWRITABLE", str(exc), data_root=str(data_root))
        return EXIT_STARTUP

    configure_logging(data_root / "logs", config.log_level, secrets=[config.token])

    lock = BackendLock(data_root / "db" / ".backend.lock")
    try:
        lock.acquire()
    except BackendLockError:
        fatal("DATA_ROOT_LOCKED", "Data-root đang được một backend khác sử dụng")
        return EXIT_STARTUP

    try:
        channel.emit(ProgressMessage(stage="binding").model_dump_json())
        try:
            sock = bind_socket(config.host, config.port)
        except OSError as exc:
            fatal("PORT_UNAVAILABLE", str(exc), port=config.port)
            return EXIT_STARTUP

        runtime = Runtime(config=config, port=sock.getsockname()[1])

        def emit_ready() -> None:
            channel.emit(ReadyMessage(port=runtime.port, pid=runtime.pid).model_dump_json())
            log.info("Backend sẵn sàng trên 127.0.0.1:%s (dev=%s)", runtime.port, args.dev)

        async def run() -> None:
            if not args.dev:
                loop = asyncio.get_running_loop()
                watch_stdin_eof(loop, lambda: runtime.request_shutdown("stdin_eof", 3000))
            await serve(runtime, sock, emit_ready)

        asyncio.run(run())
        return 0
    finally:
        lock.release()
