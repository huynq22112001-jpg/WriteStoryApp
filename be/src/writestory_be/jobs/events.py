"""EventBus chế độ RAM cho R0 (F01 be.md §C).

R1 thêm chế độ DB: event được ghi vào `job_events` trong transaction nghiệp vụ rồi mới broadcast.
Giao diện publish/subscribe/replay giữ nguyên để route SSE không phải đổi.
"""

import asyncio
import json
import sqlite3
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from writestory_be.api.events_schema import EVENT_SCHEMA_VERSION, EventEnvelope, EventType
from writestory_be.core.clock import utcnow_iso

_CLOSED = object()


def _event_bounds(connection: sqlite3.Connection) -> tuple[int | None, int]:
    oldest = connection.execute("SELECT min(seq) FROM job_events").fetchone()[0]
    try:
        latest = connection.execute(
            "SELECT max(coalesce((SELECT max(seq) FROM job_events), 0), "
            "coalesce((SELECT seq FROM sqlite_sequence WHERE name='job_events'), 0))"
        ).fetchone()[0]
    except sqlite3.OperationalError as exc:
        if "sqlite_sequence" not in str(exc):
            raise
        latest = connection.execute("SELECT coalesce(max(seq), 0) FROM job_events").fetchone()[0]
    return oldest, int(latest or 0)


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
    def __init__(
        self,
        capacity: int = 1000,
        subscriber_queue_max: int = 1000,
        *,
        database_path: Path | None = None,
        replay_max: int = 5000,
    ) -> None:
        self._buffer: deque[EventEnvelope] = deque(maxlen=capacity)
        self._seq = 0
        self._subscribers: set[Subscriber] = set()
        self._queue_max = subscriber_queue_max
        self._closed = False
        self.database_path = database_path
        self.replay_max = replay_max
        self._db_oldest_seq: int | None = None
        self._tail_last_sent: dict[tuple[str | None, str], float] = {}

    async def initialize(self) -> None:
        if self.database_path is None or not self.database_path.exists():
            return

        def read_watermark() -> tuple[int | None, int]:
            with sqlite3.connect(self.database_path) as connection:
                return _event_bounds(connection)

        self._db_oldest_seq, latest = await asyncio.to_thread(read_watermark)
        self._seq = max(self._seq, latest)

    async def has_job(self, job_id: str) -> bool:
        if self.database_path is None or not self.database_path.exists():
            return False

        def read_job() -> bool:
            with sqlite3.connect(self.database_path) as connection:
                return connection.execute(
                    "SELECT 1 FROM jobs WHERE id = ?", (job_id,)
                ).fetchone() is not None

        return await asyncio.to_thread(read_job)

    async def replay_async(
        self, since: int, *, watermark: int | None = None, job_id: str | None = None
    ) -> list[EventEnvelope] | None:
        """Replay from durable storage when configured, otherwise from the R0 ring buffer."""
        if self.database_path is None:
            replayed = self.replay(since)
            return (
                [event for event in replayed if event.job_id == job_id]
                if replayed is not None and job_id is not None
                else replayed
            )
        upper_bound = self._seq if watermark is None else watermark

        def read_rows() -> tuple[int | None, int, list[tuple]]:
            with sqlite3.connect(self.database_path) as connection:
                oldest, latest = _event_bounds(connection)
                job_filter = " AND job_id = ?" if job_id is not None else ""
                params = [since, upper_bound]
                if job_id is not None:
                    params.append(job_id)
                params.append(self.replay_max + 1)
                rows = connection.execute(
                    "SELECT seq, v, ts, type, work_id, job_id, chapter_no, payload_json "
                    "FROM job_events WHERE seq > ? AND seq <= ?"
                    + job_filter
                    + " ORDER BY seq LIMIT ?",
                    params,
                ).fetchall()
                return oldest, latest, rows

        oldest, latest, rows = await asyncio.to_thread(read_rows)
        self._db_oldest_seq = oldest
        if (
            (oldest is not None and since < oldest - 1)
            or (oldest is None and since < latest)
            or since > latest
            or len(rows) > self.replay_max
        ):
            return None
        return [
            EventEnvelope(
                seq=row[0],
                v=row[1],
                ts=row[2],
                type=row[3],
                work_id=row[4],
                job_id=row[5],
                chapter_no=row[6],
                payload=json.loads(row[7]),
                persisted=True,
            )
            for row in rows
        ]

    @property
    def watermark(self) -> int:
        return self._seq

    @property
    def oldest_seq(self) -> int | None:
        return self._db_oldest_seq or (self._buffer[0].seq if self._buffer else None)

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
        seq: int | None = None,
        ts: str | None = None,
    ) -> EventEnvelope:
        """Event được lưu (có `seq` riêng, replay được)."""
        self._seq = max(self._seq + (seq is None), seq or 0)
        envelope = EventEnvelope(
            v=EVENT_SCHEMA_VERSION,
            seq=self._seq if seq is None else seq,
            ts=ts or utcnow_iso(),
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

    def publish_tail(
        self,
        *,
        work_id: str | None,
        job_id: str,
        candidate_id: str,
        step: str,
        tail: str,
        interval_s: float = 0.25,
    ) -> EventEnvelope | None:
        now = asyncio.get_running_loop().time()
        key = (work_id, job_id)
        if now - self._tail_last_sent.get(key, 0) < interval_s:
            return None
        self._tail_last_sent[key] = now
        return self.publish_transient(
            "stream.tail",
            {"candidate_id": candidate_id, "step": step, "tail": tail[-200:]},
            work_id=work_id,
            job_id=job_id,
        )

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
