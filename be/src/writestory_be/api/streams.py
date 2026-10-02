"""Luồng sự kiện toàn cục `GET /v1/events` (Plan §23.1.C, F01 be.md §C)."""

import logging
from collections.abc import AsyncIterable
from typing import Annotated

from fastapi import APIRouter, Header, Query
from fastapi.sse import EventSourceResponse, ServerSentEvent

from writestory_be.api.dependencies import RuntimeDep
from writestory_be.api.events_schema import EventEnvelope
from writestory_be.core.errors import AppError, ErrorCode

log = logging.getLogger(__name__)
router = APIRouter()

MAX_WATCHED_WORKS = 20


def _to_sse(envelope: EventEnvelope) -> ServerSentEvent:
    data = envelope.model_dump(mode="json")
    if envelope.persisted:
        return ServerSentEvent(data=data, event=envelope.type, id=str(envelope.seq))
    # Event không lưu không có dòng `id:` để không làm lệch con trỏ Last-Event-ID.
    return ServerSentEvent(data=data, event=envelope.type)


def _parse_cursor(last_event_id: str | None, since: int | None) -> int | None:
    if last_event_id is not None:
        try:
            value = int(last_event_id)
            if value >= 0:
                return value
        except ValueError:
            log.warning("Bỏ qua Last-Event-ID không hợp lệ: %r", last_event_id)
    return since


@router.get("/v1/events", response_class=EventSourceResponse, name="stream_events")
async def stream_events(
    runtime: RuntimeDep,
    since: Annotated[int | None, Query(ge=0)] = None,
    works: Annotated[str | None, Query(description="work_id cách nhau dấu phẩy")] = None,
    previews: Annotated[int, Query(ge=0, le=1)] = 1,
    last_event_id: Annotated[str | None, Header()] = None,
) -> AsyncIterable[ServerSentEvent]:
    async for event in _stream(
        runtime,
        since=since,
        works=works,
        previews=bool(previews),
        last_event_id=last_event_id,
    ):
        yield event


@router.get(
    "/v1/jobs/{job_id}/events",
    response_class=EventSourceResponse,
    name="stream_job_events",
)
async def stream_job_events(
    job_id: str,
    runtime: RuntimeDep,
    since: Annotated[int | None, Query(ge=0)] = None,
    last_event_id: Annotated[str | None, Header()] = None,
) -> AsyncIterable[ServerSentEvent]:
    if not await runtime.event_bus.has_job(job_id):
        raise AppError(ErrorCode.NOT_FOUND, detail={"job_id": job_id})
    async for event in _stream(
        runtime,
        since=since,
        works=None,
        previews=False,
        last_event_id=last_event_id,
        job_id=job_id,
    ):
        yield event


async def _stream(
    runtime,
    *,
    since: int | None,
    works: str | None,
    previews: bool,
    last_event_id: str | None,
    job_id: str | None = None,
) -> AsyncIterable[ServerSentEvent]:
    watched = {w for w in (works or "").split(",") if w}
    if len(watched) > MAX_WATCHED_WORKS:
        raise AppError(ErrorCode.VALIDATION, detail={"field": "works", "max": MAX_WATCHED_WORKS})

    bus = runtime.event_bus
    cursor = _parse_cursor(last_event_id, since)
    start_watermark = bus.watermark
    sub = bus.subscribe()
    try:
        watermark_at_subscribe = bus.watermark
        if cursor is None:
            cursor = start_watermark
        last_sent = cursor
        replayed = await bus.replay_async(
            cursor, watermark=watermark_at_subscribe, job_id=job_id
        )
        if replayed is None:
            yield _to_sse(
                bus.make_transient(
                    "backend.notice",
                    {
                        "kind": "replay_gap",
                        "detail": {"oldest_seq": bus.oldest_seq, "latest_seq": bus.watermark},
                    },
                )
            )
            last_sent = watermark_at_subscribe
        else:
            for envelope in replayed:
                yield _to_sse(envelope)
                last_sent = max(last_sent, envelope.seq)

        while True:
            envelope = await sub.next()
            if envelope is None:
                return
            if job_id is not None and envelope.job_id != job_id:
                continue
            if envelope.persisted:
                if envelope.seq <= last_sent:
                    continue  # đã gửi trong phần replay
                last_sent = envelope.seq
            elif envelope.type == "token.delta":
                mode = envelope.payload.get("mode")
                if mode == "preview" and (not previews or envelope.work_id in watched):
                    continue
                if mode != "preview" and envelope.work_id not in watched:
                    continue
            elif envelope.type == "stream.tail":
                if not previews or envelope.work_id in watched:
                    continue
            yield _to_sse(envelope)
    finally:
        bus.unsubscribe(sub)
