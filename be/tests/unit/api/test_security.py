async def test_missing_token_is_unauthorized(app, anon_client_factory):
    async with anon_client_factory(app) as c:
        resp = await c.get("/v1/health")
    assert resp.status_code == 401
    body = resp.json()
    assert body["code"] == "UNAUTHORIZED"
    assert body["action"] == "reload"
    assert resp.headers["X-Request-Id"] == body["request_id"]


async def test_wrong_token(client):
    resp = await client.get("/v1/health", headers={"Authorization": "Bearer nope"})
    assert resp.status_code == 401


async def test_token_in_query_is_not_accepted(app, anon_client_factory, token):
    async with anon_client_factory(app) as c:
        resp = await c.get(f"/v1/health?token={token}")
    assert resp.status_code == 401


async def test_wrong_host_rejected(client):
    resp = await client.get("/v1/health", headers={"Host": "evil.example:8765"})
    assert resp.status_code == 400
    assert resp.json()["code"] == "FORBIDDEN_HOST"


async def test_localhost_host_rejected_outside_dev(client):
    resp = await client.get("/v1/health", headers={"Host": "localhost:8765"})
    assert resp.json()["code"] == "FORBIDDEN_HOST"


async def test_unknown_origin_rejected(client):
    resp = await client.get("/v1/health", headers={"Origin": "http://evil.example"})
    assert resp.status_code == 403
    assert resp.json()["code"] == "FORBIDDEN_ORIGIN"


async def test_allowed_origin_gets_cors_headers(client, origin):
    resp = await client.get("/v1/health", headers={"Origin": origin})
    assert resp.status_code == 200
    assert resp.headers["access-control-allow-origin"] == origin
    assert "X-Request-Id" in resp.headers["access-control-expose-headers"]


async def test_preflight_without_token(app, anon_client_factory, origin):
    async with anon_client_factory(app) as c:
        resp = await c.options(
            "/v1/health",
            headers={
                "Origin": origin,
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "authorization",
            },
        )
    assert resp.status_code == 200
    assert resp.headers["access-control-allow-origin"] == origin


async def test_dev_docs_public_but_api_still_needs_token(make_runtime, anon_client_factory):
    from writestory_be.main import create_app

    dev_app = create_app(make_runtime(dev=True))
    async with anon_client_factory(dev_app) as c:
        assert (await c.get("/openapi.json")).status_code == 200
        assert (await c.get("/v1/health")).status_code == 401


async def test_shutting_down_rejects_new_requests(runtime, client):
    runtime.shutting_down = True
    resp = await client.post("/v1/dev/mock-runs", json={})
    assert resp.status_code == 503
    assert resp.json()["code"] == "BACKEND_SHUTTING_DOWN"
    # health vẫn trả lời để Rust theo dõi được quá trình tắt.
    assert (await client.get("/v1/health")).status_code == 200
