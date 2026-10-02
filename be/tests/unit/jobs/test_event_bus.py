import asyncio

from writestory_be.jobs.events import EventBus


def test_publish_increments_seq_and_replays():
    bus = EventBus()
    a = bus.publish("job.queued", {"job_type": "write"}, work_id="w1")
    b = bus.publish("job.state", {"status": "running"}, work_id="w1")
    assert (a.seq, b.seq) == (1, 2)
    assert bus.watermark == 2
    assert [e.seq for e in bus.replay(0)] == [1, 2]
    assert [e.seq for e in bus.replay(1)] == [2]
    assert bus.replay(2) == []


def test_replay_reports_gap_when_events_evicted():
    bus = EventBus(capacity=3)
    for i in range(5):
        bus.publish("job.step", {"i": i})
    assert bus.oldest_seq == 3
    assert bus.replay(0) is None  # seq 1 và 2 đã mất, cần replay_gap
    assert [e.seq for e in bus.replay(2)] == [3, 4, 5]


def test_transient_events_not_stored_and_keep_watermark():
    bus = EventBus()
    bus.publish("job.step", {})
    delta = bus.publish_transient("token.delta", {"text": "a"}, work_id="w1")
    assert delta.seq == 1 and not delta.persisted
    assert bus.watermark == 1
    assert [e.type for e in bus.replay(0)] == ["job.step"]


async def test_subscriber_receives_live_events_then_close():
    bus = EventBus()
    sub = bus.subscribe()
    bus.publish("queue.changed", {"n": 1})
    received = await asyncio.wait_for(sub.next(), 1)
    assert received.payload == {"n": 1}
    bus.close_all()
    assert await sub.next() is None


async def test_slow_subscriber_is_cut_off():
    bus = EventBus(subscriber_queue_max=2)
    slow = bus.subscribe()
    for i in range(3):
        bus.publish("job.step", {"i": i})
    assert slow.lagging
    assert (await slow.next()).payload == {"i": 0}
    assert (await slow.next()).payload == {"i": 1}
    assert await slow.next() is None  # bị cắt; client sẽ nối lại bằng Last-Event-ID


async def test_subscribe_after_close_returns_closed():
    bus = EventBus()
    bus.close_all()
    assert await bus.subscribe().next() is None


async def test_stream_tail_is_rate_limited_and_bounded():
    bus = EventBus()
    tail = bus.publish_tail(
        work_id="work",
        job_id="job",
        candidate_id="candidate",
        step="writer",
        tail="x" * 240,
    )
    assert tail is not None
    assert tail.type == "stream.tail"
    assert len(tail.payload["tail"]) == 200
    assert bus.publish_tail(
        work_id="work",
        job_id="job",
        candidate_id="candidate",
        step="writer",
        tail="new tail",
    ) is None
