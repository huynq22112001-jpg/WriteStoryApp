"""Luồng sự kiện toàn cục `GET /v1/events` (Plan §23.1.C, F01 be.md §C)."""

import logging
from collections.abc import AsyncIterable
from typing import Annotated

from fastapi import APIRouter, Header, Query
from fastapi.sse import EventSourceResponse, ServerSentEvent

from writestory_be.api.dependencies import RuntimeDep
from writestory_be.api.events_schema import TRANSIENT_TYPES, EventEnvelope
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
    last_event_id: Annotated[str | None, Header()] = None,
) -> AsyncIterable[ServerSentEvent]:
    watched = {w for w in (works or "").split(",") if w}
    if len(watched) > MAX_WATCHED_WORKS:
        raise AppError(ErrorCode.VALIDATION, detail={"field": "works", "max": MAX_WATCHED_WORKS})

    bus = runtime.event_bus
    # Đăng ký trước rồi mới replay để không sót event phát ra giữa hai bước.
    sub = bus.subscribe()
    try:
        cursor = _parse_cursor(last_event_id, since)
        last_sent = bus.watermark if cursor is None else cursor

        if cursor is not None:
            replayed = bus.replay(cursor)
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
                last_sent = bus.watermark
            else:
                for envelope in replayed:
                    yield _to_sse(envelope)
                    last_sent = envelope.seq

        while True:
            envelope = await sub.next()
            if envelope is None:
                return
            if envelope.persisted:
                if envelope.seq <= last_sent:
                    continue  # đã gửi trong phần replay
                last_sent = envelope.seq
            elif envelope.type in TRANSIENT_TYPES and envelope.work_id not in watched:
                continue
            yield _to_sse(envelope)
    finally:
        bus.unsubscribe(sub)
