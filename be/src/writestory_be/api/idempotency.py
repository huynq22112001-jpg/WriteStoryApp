from __future__ import annotations

import hashlib
import json
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from fastapi import Request
from fastapi.encoders import jsonable_encoder

from writestory_be.core.clock import to_iso, utcnow
from writestory_be.core.errors import AppError, ErrorCode
from writestory_be.infrastructure.db.models.system import IdempotencyRecord
from writestory_be.infrastructure.db.unit_of_work import UnitOfWork, WriteContext

IDEMPOTENCY_TTL_HOURS = 24
Operation = Callable[[WriteContext], Awaitable[tuple[int, dict[str, Any]]]]


@dataclass(frozen=True)
class IdempotencyResult:
    status_code: int
    body: dict[str, Any]
    replayed: bool = False


def canonical_json(value: Any) -> str:
    return json.dumps(
        jsonable_encoder(value),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def request_hash(method: str, path: str, body: Any) -> str:
    canonical = f"{method.upper()}\n{path}\n{canonical_json(body)}"
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def idempotency_key_from_request(request: Request) -> str:
    key = request.headers.get("Idempotency-Key", "").strip()
    if not key:
        raise AppError(ErrorCode.VALIDATION, detail={"field": "Idempotency-Key"})
    return key


class IdempotencyService:
    def __init__(self, uow: UnitOfWork) -> None:
        self.uow = uow

    async def execute(
        self,
        *,
        key: str,
        method: str,
        path: str,
        body: Any,
        operation: Operation,
    ) -> IdempotencyResult:
        if not key.strip():
            raise AppError(ErrorCode.VALIDATION, detail={"field": "Idempotency-Key"})
        method = method.upper()
        digest = request_hash(method, path, body)
        now = utcnow()
        now_iso = to_iso(now)

        async def write(ctx: WriteContext) -> IdempotencyResult:
            identity = (key, method, path)
            record = await ctx.session.get(IdempotencyRecord, identity)
            if record is not None and record.expires_at > now_iso:
                if record.request_hash != digest:
                    raise AppError(
                        ErrorCode.IDEMPOTENCY_CONFLICT,
                        detail={"method": method, "path": path},
                    )
                return IdempotencyResult(
                    status_code=record.status_code,
                    body=json.loads(record.response_json),
                    replayed=True,
                )
            if record is not None:
                await ctx.session.delete(record)

            status_code, response_body = await operation(ctx)
            encoded = canonical_json(response_body)
            ctx.session.add(
                IdempotencyRecord(
                    key=key,
                    method=method,
                    path=path,
                    request_hash=digest,
                    status_code=status_code,
                    response_json=encoded,
                    created_at=now_iso,
                    expires_at=to_iso(now + timedelta(hours=IDEMPOTENCY_TTL_HOURS)),
                )
            )
            return IdempotencyResult(status_code=status_code, body=json.loads(encoded))

        return await self.uow.write(write)
