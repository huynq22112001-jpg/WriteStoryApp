"""SSE qua server uvicorn thật với socket bind trước (giống chế độ desktop)."""

import asyncio
import json
from contextlib import asynccontextmanager

import httpx
import uvicorn

from writestory_be.bootstrap.runtime import bind_socket
from writestory_be.main import create_app


@asynccontextmanager
async def running_server(make_runtime, *, dev: bool = False):
    sock = bind_socket("127.0.0.1", 0)
    runtime = make_runtime(dev=dev, port=sock.getsockname()[1])
    server = uvicorn.Server(
        uvicorn.Config(create_app(runtime), lifespan="off", log_config=None, access_log=False)
    )
    runtime.server = server
    task = asyncio.create_task(server.serve(sockets=[sock]))
    while not server.started:
        await asyncio.sleep(0.02)
    try:
        yield runtime, f"http://127.0.0.1:{runtime.port}"
    finally:
        runtime.event_bus.close_all()
        server.should_exit = True
        await asyncio.wait_for(task, 10)


async def read_events(response: httpx.Response, count: int) -> list[dict]:
    """Đọc `count` event SSE; trả về list {event, id, data}."""
    events: list[dict] = []
    current: dict = {}
    async for line in response.aiter_lines():
        if line == "":
            if "data" in current:
                events.append(current)
                if len(events) == count:
                    return events
            current = {}
            continue
        if line.startswith(":"):
            continue  # comment / ping
        field, _, value = line.partition(":")
        value = value.removeprefix(" ")
        current[field] = json.loads(value) if field == "data" else value
    return events


async def test_replay_and_live_events(make_runtime, token):
    async with running_server(make_runtime) as (runtime, url):
        bus = runtime.event_bus
        bus.publish("job.queued", {"job_type": "write"}, work_id="w1")
        bus.publish("job.state", {"status": "running"}, work_id="w1")

        headers = {"Authorization": f"Bearer {token}"}
        async with httpx.AsyncClient(timeout=10) as client:
            async with client.stream("GET", f"{url}/v1/events?since=1", headers=headers) as resp:
                assert resp.status_code == 200
                assert resp.headers["content-type"].startswith("text/event-stream")

                async def publish_later():
                    await asyncio.sleep(0.2)
                    bus.publish("chapter.committed", {"chapter_no": 1}, work_id="w1")

                asyncio.create_task(publish_later())
                events = await asyncio.wait_for(read_events(resp, 2), 5)

    assert [e["event"] for e in events] == ["job.state", "chapter.committed"]
    assert [e["id"] for e in events] == ["2", "3"]
    assert events[0]["data"]["seq"] == 2
    assert "persisted" not in events[0]["data"]


async def test_last_event_id_overrides_since(make_runtime, token):
    async with running_server(make_runtime) as (runtime, url):
        for i in range(3):
            runtime.event_bus.publish("job.step", {"i": i})
        headers = {"Authorization": f"Bearer {token}", "Last-Event-ID": "2"}
        async with httpx.AsyncClient(timeout=10) as client:
            async with client.stream("GET", f"{url}/v1/events?since=0", headers=headers) as resp:
                events = await asyncio.wait_for(read_events(resp, 1), 5)
    assert events[0]["id"] == "3"


async def test_token_delta_only_for_watched_work(make_runtime, token):
    async with running_server(make_runtime) as (runtime, url):
        bus = runtime.event_bus
        headers = {"Authorization": f"Bearer {token}"}
        async with httpx.AsyncClient(timeout=10) as client:
            async with client.stream("GET", f"{url}/v1/events?works=w2", headers=headers) as resp:

                async def publish_later():
                    await asyncio.sleep(0.2)
                    bus.publish_transient("token.delta", {"text": "bỏ qua"}, work_id="w1")
                    bus.publish_transient("token.delta", {"text": "nhận"}, work_id="w2")
                    bus.publish("job.state", {"status": "succeeded"}, work_id="w1")

                asyncio.create_task(publish_later())
                events = await asyncio.wait_for(read_events(resp, 2), 5)

    assert events[0]["event"] == "token.delta"
    assert events[0]["data"]["payload"]["text"] == "nhận"
    assert "id" not in events[0]  # event không lưu không có dòng id
    assert events[1]["event"] == "job.state"


async def test_replay_gap_notice(make_runtime, token):
    async with running_server(make_runtime) as (runtime, url):
        runtime.event_bus = bus = type(runtime.event_bus)(capacity=2)
        for i in range(5):
            bus.publish("job.step", {"i": i})
        headers = {"Authorization": f"Bearer {token}"}
        async with httpx.AsyncClient(timeout=10) as client:
            async with client.stream("GET", f"{url}/v1/events?since=0", headers=headers) as resp:
                events = await asyncio.wait_for(read_events(resp, 1), 5)
    assert events[0]["event"] == "backend.notice"
    assert events[0]["data"]["payload"]["kind"] == "replay_gap"


async def test_mock_runs_stream_tokens_for_several_works(make_runtime, token):
    async with running_server(make_runtime, dev=True) as (runtime, url):
        headers = {"Authorization": f"Bearer {token}"}
        async with httpx.AsyncClient(timeout=10) as client:
            async with client.stream(
                "GET", f"{url}/v1/events?works=mock-work-1,mock-work-2", headers=headers
            ) as resp:
                created = await client.post(
                    f"{url}/v1/dev/mock-runs",
                    json={"works": 2, "latency_ms": 0, "tokens_per_sec": 500, "repeat": 1},
                    headers=headers,
                )
                assert created.status_code == 202
                events = await asyncio.wait_for(read_events(resp, 60), 10)

    tokens_by_work: dict[str, int] = {}
    for e in events:
        if e["event"] == "token.delta":
            work = e["data"]["work_id"]
            tokens_by_work[work] = tokens_by_work.get(work, 0) + 1
    assert set(tokens_by_work) == {"mock-work-1", "mock-work-2"}
