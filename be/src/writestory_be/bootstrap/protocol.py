"""Giao thức giữa Tauri (Rust) và backend Python (F00 be.md §B).

Rust ghi đúng một dòng JSON `BootstrapConfig` vào stdin rồi giữ stdin mở; backend trả các dòng
NDJSON trên kênh protocol (stdout gốc): `progress`, `ready`, `fatal`.
"""

from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

BACKEND_PROTOCOL_VERSION = 1


class BootstrapConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")

    protocol_version: int
    token: str = Field(repr=False, min_length=1)
    data_root: Path
    data_id: str | None = None
    parent_pid: int | None = None
    app_version: str = "0.1.0"
    allowed_origins: list[str] = Field(default_factory=list)
    dev_features: bool = False
    log_level: Literal["debug", "info", "warning", "error"] = "info"
    host: str = "127.0.0.1"
    port: int = Field(default=0, ge=0, le=65535)  # 0 = hệ điều hành cấp cổng trống


class ProgressMessage(BaseModel):
    event: Literal["progress"] = "progress"
    stage: str


class ReadyMessage(BaseModel):
    event: Literal["ready"] = "ready"
    port: int
    protocol_version: int = BACKEND_PROTOCOL_VERSION
    pid: int


class FatalMessage(BaseModel):
    event: Literal["fatal"] = "fatal"
    code: str
    message: str
    detail: dict[str, Any] = Field(default_factory=dict)


class ProtocolMismatchError(Exception):
    pass


def parse_bootstrap_line(line: str) -> BootstrapConfig:
    config = BootstrapConfig.model_validate_json(line)
    if config.protocol_version != BACKEND_PROTOCOL_VERSION:
        raise ProtocolMismatchError(
            f"protocol_version {config.protocol_version} != {BACKEND_PROTOCOL_VERSION}"
        )
    return config
