"""EventBus chế độ RAM cho R0 (F01 be.md §C).

R1 thêm chế độ DB: event được ghi vào `job_events` trong transaction nghiệp vụ rồi mới broadcast.
Giao diện publish/subscribe/replay giữ nguyên để route SSE không phải đổi.
"""

import asyncio
from collections import deque
from dataclasses import dataclass, field
from typing import Any

from writestory_be.api.events_schema import EVENT_SCHEMA_VERSION, EventEnvelope, EventType
from writestory_be.core.clock import utcnow_iso

_CLOSED = object()


@dataclass(eq=False)
class Subscriber:
    queue: asyncio.Queue[Any]
    lagging: bool = False
    closed: bool = field(default=False)

    async def next(self) -> EventEnvelope | None:
        """Event kế tiếp; `None` khi bus đóng hoặc subscriber bị cắt vì chậm."""
        item = await self.queue.get()
        if item is _CLOSED:
            self.closed = True
            return None
        return item


class EventBus:
    def __init__(self, capacity: int = 1000, subscriber_queue_max: int = 1000) -> None:
        self._buffer: deque[EventEnvelope] = deque(maxlen=capacity)
        self._seq = 0
        self._subscribers: set[Subscriber] = set()
        self._queue_max = subscriber_queue_max
        self._closed = False

    @property
    def watermark(self) -> int:
        return self._seq

    @property
    def oldest_seq(self) -> int | None:
        return self._buffer[0].seq if self._buffer else None

    def subscribe(self) -> Subscriber:
        sub = Subscriber(queue=asyncio.Queue(maxsize=self._queue_max + 1))
        if self._closed:
            sub.queue.put_nowait(_CLOSED)
        else:
            self._subscribers.add(sub)
        return sub

    def unsubscribe(self, sub: Subscriber) -> None:
        self._subscribers.discard(sub)

    def publish(
        self,
        type: EventType,
        payload: dict[str, Any],
        *,
        work_id: str | None = None,
        job_id: str | None = None,
        chapter_no: int | None = None,
    ) -> EventEnvelope:
        """Event được lưu (có `seq` riêng, replay được)."""
        self._seq += 1
        envelope = EventEnvelope(
            v=EVENT_SCHEMA_VERSION,
            seq=self._seq,
            ts=utcnow_iso(),
            type=type,
            work_id=work_id,
            job_id=job_id,
            chapter_no=chapter_no,
            payload=payload,
            persisted=True,
        )
        self._buffer.append(envelope)
        self._fan_out(envelope)
        return envelope

    def publish_transient(
        self,
        type: EventType,
        payload: dict[str, Any],
        *,
        work_id: str | None = None,
        job_id: str | None = None,
        chapter_no: int | None = None,
    ) -> EventEnvelope:
        """Event không lưu (ví dụ `token.delta`): `seq` = watermark hiện tại, không replay."""
        envelope = self.make_transient(
            type, payload, work_id=work_id, job_id=job_id, chapter_no=chapter_no
        )
        self._fan_out(envelope)
        return envelope

    def make_transient(
        self,
        type: EventType,
        payload: dict[str, Any],
        *,
        work_id: str | None = None,
        job_id: str | None = None,
        chapter_no: int | None = None,
    ) -> EventEnvelope:
        """Tạo envelope không lưu mà không phát cho ai (dùng cho thông báo riêng một client)."""
        return EventEnvelope(
            v=EVENT_SCHEMA_VERSION,
            seq=self._seq,
            ts=utcnow_iso(),
            type=type,
            work_id=work_id,
            job_id=job_id,
            chapter_no=chapter_no,
            payload=payload,
            persisted=False,
        )

    def replay(self, since: int) -> list[EventEnvelope] | None:
        """Event có `seq > since`. `None` nếu đã mất event trong khoảng đó (cần `replay_gap`)."""
        if since >= self._seq:
            return []
        oldest = self.oldest_seq
        if oldest is None or since < oldest - 1:
            return None
        return [e for e in self._buffer if e.seq > since]

    def close_all(self) -> None:
        self._closed = True
        for sub in list(self._subscribers):
            self._close(sub)

    def _fan_out(self, envelope: EventEnvelope) -> None:
        for sub in list(self._subscribers):
            if sub.queue.qsize() >= self._queue_max:
                # Client quá chậm: cắt stream, client nối lại bằng Last-Event-ID (F01 §C.5).
                sub.lagging = True
                self._close(sub)
                continue
            sub.queue.put_nowait(envelope)

    def _close(self, sub: Subscriber) -> None:
        self._subscribers.discard(sub)
        sub.queue.put_nowait(_CLOSED)
