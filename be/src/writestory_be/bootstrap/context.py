import asyncio
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

from writestory_be.bootstrap.protocol import BootstrapConfig
from writestory_be.core.clock import utcnow_iso
from writestory_be.infrastructure.db.engine import create_engine, database_path
from writestory_be.infrastructure.db.unit_of_work import UnitOfWork
from writestory_be.infrastructure.db.writer import WriterQueue
from writestory_be.infrastructure.secrets.secret_store import SecretStore
from writestory_be.infrastructure.secrets.session_store import SessionSecretStore
from writestory_be.infrastructure.secrets.vault import VaultService
from writestory_be.jobs.events import EventBus
from writestory_be.modules.vault.settings import VaultSettingsState, VaultSettingsStore

if TYPE_CHECKING:
    import uvicorn

DATA_SUBDIRS = ("db", "assets", "imports", "exports", "backups", "logs", "cache", "tmp")


@dataclass
class Runtime:
    """Trạng thái của một phiên backend. Data-root luôn là đường dẫn tuyệt đối từ bootstrap
    (Plan §3), không suy ra từ thư mục làm việc."""

    config: BootstrapConfig
    event_bus: EventBus = field(default_factory=EventBus)
    started_at: str = field(default_factory=utcnow_iso)
    pid: int = field(default_factory=os.getpid)
    port: int | None = None
    schema_version: str | None = None
    interrupted_jobs: list[str] = field(default_factory=list)
    interrupted_job_count: int = 0
    shutting_down: bool = False
    server: uvicorn.Server | None = None
    background_tasks: set[asyncio.Task[Any]] = field(default_factory=set)
    vault: VaultService = field(init=False)
    session_secrets: SessionSecretStore = field(default_factory=SessionSecretStore)
    secrets: SecretStore = field(init=False)
    vault_settings_store: VaultSettingsStore = field(init=False)
    db_engine: Any | None = field(init=False, default=None)
    db_sessions: Any | None = field(init=False, default=None)
    writer_queue: WriterQueue | None = field(init=False, default=None)
    uow: UnitOfWork | None = field(init=False, default=None)
    provider_limiter: Any = field(init=False, default=None)

    def __post_init__(self) -> None:
        from writestory_be.infrastructure.ai.limits import ProviderLimiter

        self.provider_limiter = ProviderLimiter()
        self.vault = VaultService(self.config.data_root / "secrets.enc")
        self.secrets = SecretStore(self.vault, self.session_secrets)
        self.vault_settings_store = VaultSettingsStore(
            self.config.data_root / "db" / "app.sqlite3", VaultSettingsState()
        )

    def ensure_database_services(self) -> UnitOfWork:
        if self.uow is None:
            from sqlalchemy.ext.asyncio import async_sessionmaker

            self.db_engine = create_engine(database_path(self.data_root))
            self.db_sessions = async_sessionmaker(self.db_engine, expire_on_commit=False)
            self.writer_queue = WriterQueue(self.db_sessions, self.event_bus)
            self.uow = UnitOfWork(self.db_sessions, self.writer_queue)
        return self.uow

    @property
    def data_root(self) -> Path:
        return self.config.data_root

    @classmethod
    def for_schema_export(cls) -> Runtime:
        """Runtime không side effect, chỉ để dựng app xuất OpenAPI (Arch §7)."""
        return cls(
            config=BootstrapConfig(
                protocol_version=1, token="schema-export", data_root=Path("."), dev_features=True
            )
        )

    def allowed_hosts(self) -> set[str]:
        if self.port is None:
            return set()
        hosts = {f"127.0.0.1:{self.port}"}
        if self.config.dev_features:
            hosts.add(f"localhost:{self.port}")
        return hosts

    def spawn(self, coro: Any) -> asyncio.Task[Any]:
        """Giữ tham chiếu task nền để không bị thu gom giữa chừng."""
        task = asyncio.create_task(coro)
        self.background_tasks.add(task)
        task.add_done_callback(self.background_tasks.discard)
        return task

    def request_shutdown(self, reason: str, deadline_ms: int = 5000) -> None:
        if self.shutting_down:
            return
        self.shutting_down = True
        self.event_bus.publish(
            "backend.notice",
            {"kind": "shutting_down", "detail": {"reason": reason, "deadline_ms": deadline_ms}},
        )
        self.event_bus.close_all()
        for task in list(self.background_tasks):
            task.cancel()
        if self.server is not None:
            server = self.server
            # Trễ ngắn để response của POST /v1/system/shutdown kịp gửi về.
            asyncio.get_running_loop().call_later(0.05, setattr, server, "should_exit", True)


def prepare_data_root(root: Path) -> None:
    """Tạo các thư mục con còn thiếu (Plan §3.1) và kiểm tra quyền ghi thật."""
    root.mkdir(parents=True, exist_ok=True)
    for name in DATA_SUBDIRS:
        (root / name).mkdir(exist_ok=True)
    probe = root / "tmp" / f".write-test-{os.getpid()}"
    probe.write_bytes(b"ok")
    probe.unlink()
