from typing import Literal

from fastapi import APIRouter, status
from pydantic import BaseModel, Field

from writestory_be.api.dependencies import RuntimeDep
from writestory_be.bootstrap.protocol import BACKEND_PROTOCOL_VERSION

router = APIRouter(prefix="/v1", tags=["system"])


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"
    protocol_version: int
    app_version: str
    schema_version: str | None = Field(
        default=None, description="Revision Alembic hiện tại; None tới khi F02 có migration"
    )
    data_id: str | None
    started_at: str
    pid: int


class ShutdownRequest(BaseModel):
    reason: Literal["app_exit", "restart"]
    deadline_ms: int = Field(default=5000, ge=0, le=60_000)


class ShutdownAccepted(BaseModel):
    accepted: bool = True
    deadline_ms: int


@router.get("/health", name="health")
async def health(runtime: RuntimeDep) -> HealthResponse:
    return HealthResponse(
        protocol_version=BACKEND_PROTOCOL_VERSION,
        app_version=runtime.config.app_version,
        data_id=runtime.config.data_id,
        started_at=runtime.started_at,
        pid=runtime.pid,
    )


@router.post("/system/shutdown", status_code=status.HTTP_202_ACCEPTED, name="shutdown")
async def shutdown(body: ShutdownRequest, runtime: RuntimeDep) -> ShutdownAccepted:
    runtime.request_shutdown(body.reason, body.deadline_ms)
    return ShutdownAccepted(deadline_ms=body.deadline_ms)
