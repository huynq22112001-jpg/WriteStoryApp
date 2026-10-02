from fastapi import APIRouter

from writestory_be.core.errors import AppError, ErrorCode, default_retryable, http_status
from writestory_be.main import create_app


async def test_health(client, runtime):
    resp = await client.get("/v1/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["protocol_version"] == 1
    assert body["data_id"] == "test-data-id"
    assert body["pid"] == runtime.pid
    assert body["started_at"].endswith("Z")


async def test_unknown_route_is_not_found_contract(client):
    resp = await client.get("/v1/khong-ton-tai")
    assert resp.status_code == 404
    body = resp.json()
    assert body["code"] == "NOT_FOUND"
    assert body["retryable"] is False
    assert body["request_id"]


async def test_validation_error_lists_fields(client):
    resp = await client.post("/v1/system/shutdown", json={"reason": "bất kỳ"})
    assert resp.status_code == 422
    body = resp.json()
    assert body["code"] == "VALIDATION"
    assert body["detail"]["fields"][0]["loc"][-1] == "reason"


async def test_app_error_and_unexpected_error(runtime, anon_client_factory, token):
    app = create_app(runtime)
    router = APIRouter()

    @router.get("/v1/test/conflict")
    async def conflict():
        raise AppError(ErrorCode.REVISION_CONFLICT, detail={"current_revision": 3})

    @router.get("/v1/test/boom")
    async def boom():
        raise RuntimeError("bí mật nội bộ")

    app.include_router(router)
    async with anon_client_factory(app) as c:
        c.headers["Authorization"] = f"Bearer {token}"
        conflict_resp = await c.get("/v1/test/conflict")
        boom_resp = await c.get("/v1/test/boom")

    assert conflict_resp.status_code == 409
    assert conflict_resp.json()["action"] == "view_diff"
    assert conflict_resp.json()["detail"] == {"current_revision": 3}

    assert boom_resp.status_code == 500
    body = boom_resp.json()
    assert body["code"] == "INTERNAL"
    assert "bí mật" not in boom_resp.text  # không lộ chi tiết lỗi/stack trace


def test_every_error_code_has_http_status():
    for code in ErrorCode:
        assert 400 <= http_status(code) <= 599


def test_provider_server_error_is_retryable_bad_gateway():
    assert http_status(ErrorCode.PROVIDER_SERVER_ERROR) == 502
    assert default_retryable(ErrorCode.PROVIDER_SERVER_ERROR)


async def test_shutdown_request_marks_runtime(client, runtime):
    events = runtime.event_bus.subscribe()
    resp = await client.post(
        "/v1/system/shutdown",
        json={"reason": "app_exit", "deadline_ms": 1000},
    )
    assert resp.status_code == 202
    assert resp.json() == {"accepted": True, "deadline_ms": 1000}
    assert runtime.shutting_down
    notice = await events.next()
    assert notice.type == "backend.notice"
    assert notice.payload["kind"] == "shutting_down"
    assert await events.next() is None  # bus đóng → stream SSE kết thúc


async def test_dev_routes_absent_outside_dev(client):
    assert (await client.post("/v1/dev/mock-runs", json={})).status_code == 404


def test_openapi_has_operation_ids_and_error_schema():
    schema = create_app().openapi()
    op_ids = {op["operationId"] for path in schema["paths"].values() for op in path.values()}
    assert {"health", "shutdown", "stream_events", "create_mock_runs"} <= op_ids
    assert "ErrorResponse" in schema["components"]["schemas"]
