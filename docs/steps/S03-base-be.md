# S03 — Base package BE (`writestory-be`)

Trạng thái: code-ready (chờ S00 để chạy test). Tính năng: F00 (bootstrap, bảo mật), F01 (lỗi, sự kiện), F02 (SQLite engine). Phụ thuộc: S01, S02.

## Mục tiêu

Backend FastAPI chạy được ở hai chế độ:

- **desktop**: Tauri gửi `BootstrapConfig` qua stdin, backend bind cổng do OS cấp, in `ready` qua stdout (F00 be.md §B).
- **dev**: chạy tay với `--dev`, cổng cố định, token dev, cho phép origin Vite (S06).

## Việc cần làm

- [x] `be/pyproject.toml` (fastapi ≥ 0.135, uvicorn, sqlalchemy[asyncio], aiosqlite, alembic, `writestory-ai` workspace).
- [x] `core/ids.py` (UUIDv7), `core/clock.py` (ISO 8601 UTC), `core/errors.py` (`ErrorCode`, `ErrorAction`, `AppError`, bảng HTTP status).
- [x] `api/errors.py`: `ErrorResponse` + exception handler cho `AppError`, lỗi validate, `HTTPException`, `Exception` (không lộ stack trace).
- [x] `api/request_id.py`: header `X-Request-Id`.
- [x] `api/security.py`: `LocalSecurityMiddleware` (Host, Origin, Bearer token so bằng `hmac.compare_digest`, preflight).
- [x] `api/events_schema.py` + `jobs/events.py`: `EventEnvelope`, `EventBus` chế độ RAM (ring buffer, seq tăng dần, subscribe trước rồi replay, chống trùng).
- [x] `api/streams.py`: `GET /v1/events` (`EventSourceResponse`, `since`, `Last-Event-ID`, `works`, `replay_gap`).
- [x] `modules/system/router.py`: `GET /v1/health`, `POST /v1/system/shutdown`.
- [x] `bootstrap/protocol.py`, `bootstrap/runtime.py`, `bootstrap/lifecycle.py`, `__main__.py`: đọc stdin, khóa `db/.backend.lock`, tạo thư mục data, bind socket, uvicorn `serve(sockets=[sock])`, in `ready`, tắt khi stdin EOF.
- [x] `infrastructure/db/engine.py`: engine `sqlite+aiosqlite`, pragma WAL / `foreign_keys` / `busy_timeout` / `synchronous=FULL`.
- [x] `main.py`: `create_app(runtime | None)` không side effect (dùng cho xuất OpenAPI).
- [x] Test: lỗi, bảo mật, health, EventBus, SSE qua server uvicorn thật, engine pragma, bootstrap protocol.
- [ ] Alembic + migration baseline → làm ở bước F02 (R1).

## Lệnh

```bash
uv run pytest be/tests -q
```

```bash
uv run python -m writestory_be --dev
```

## Tiêu chí xong

- Test `be/tests` pass.
- `--dev`: `curl -H "Authorization: Bearer dev-token" http://127.0.0.1:8765/v1/health` trả `status: ok`; thiếu token → 401 `UNAUTHORIZED` theo hợp đồng lỗi.
- Chế độ desktop: gửi một dòng JSON vào stdin → stdout in `{"event":"ready","port":…}`; đóng stdin → tiến trình thoát.

## Ghi chú

Spec: [F00 be.md](../features/F00-nen-tang-desktop/be.md), [F01 be.md](../features/F01-hop-dong-api-va-su-kien/be.md), [F02 be.md](../features/F02-nen-du-lieu/be.md). Test luồng: [T01](../tests/flows/T01-khoi-dong-va-data-root.md), [T17](../tests/flows/T17-phong-viet-va-su-kien.md).
