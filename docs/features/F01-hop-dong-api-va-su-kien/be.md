# F01 — Backend

## Module và file

```text
be/src/writestory_be/
  main.py                    create_app(runtime | None): không mở vault, không migrate, không chạy job (Arch §7)
  core/ids.py                new_id() → UUIDv7 dạng text (Python 3.14 uuid.uuid7())
  core/clock.py              utcnow() → ISO 8601 UTC, độ chính xác ms, hậu tố "Z"
  core/errors.py             AppError(code, status, detail, retryable, action), ErrorCode (StrEnum)
  api/errors.py              ErrorResponse (Pydantic), exception handlers, bảng code → HTTP status
  api/conventions.py         Page[T], CursorParams, decode/encode cursor, ExpectedRevision, Accepted202
  api/idempotency.py         Dependency idempotent(): đọc Idempotency-Key, lưu/trả lại response
  api/request_id.py          Middleware X-Request-Id (sinh nếu thiếu), gắn vào log và ErrorResponse
  api/streams.py             Route GET /v1/events, GET /v1/jobs/{id}/events (EventSourceResponse)
  api/events_schema.py       EventEnvelope (union theo type) + payload models, EVENT_SCHEMA_VERSION = 1
  api/openapi.py             custom_openapi(): operationId = route.name, chèn EventEnvelope vào components
  jobs/events.py             EventBus: publish/subscribe, watermark seq, flush token.delta, preview
  infrastructure/ai/progress_adapter.py   Triển khai ProgressSink (ai.md) → EventBus/job_steps
  infrastructure/db/repositories/job_events.py
tools/contracts/
  export_openapi.py          create_app(None) → contracts/openapi.json (sort_keys, indent 2, newline cuối)
  check_contracts.py         Chạy export + `pnpm --filter fe gen:api`, fail nếu git diff khác rỗng
contracts/examples/          error.json, event-*.json (không chứa secret)
```

## Dữ liệu và migration

| Bảng | Cột chính | Ràng buộc / index | Ghi chú |
|---|---|---|---|
| `job_events` | `seq INTEGER PRIMARY KEY AUTOINCREMENT`, `v INTEGER NOT NULL`, `ts TEXT NOT NULL`, `type TEXT NOT NULL`, `work_id TEXT NULL`, `job_id TEXT NULL`, `chapter_no INTEGER NULL`, `payload_json TEXT NOT NULL` | `ix_job_events_work_seq(work_id, seq)`, `ix_job_events_job_seq(job_id, seq)`, `ix_job_events_ts(ts)` | `AUTOINCREMENT` bảo đảm seq không bị dùng lại sau khi xóa theo retention. Không lưu `token.delta` |
| `idempotency_records` | `key TEXT`, `method TEXT`, `path TEXT`, `request_hash TEXT`, `status_code INTEGER`, `response_json TEXT`, `created_at TEXT`, `expires_at TEXT` | PK `(key, method, path)`; `ix_idempotency_expires(expires_at)` | Cho POST không tạo job. POST tạo job dùng `jobs.idempotency_key` (unique, F02) |

Migration nằm trong baseline của F02: `be/migrations/versions/0001_baseline.py` (F02 sở hữu file, F01 sở hữu định nghĩa hai bảng trên). Không có backfill. Ở R0 chưa có DB: `EventBus` chạy chế độ RAM (ring buffer 1.000 event, seq bắt đầu từ 1 mỗi lần chạy) chỉ cho spike.

## API

| Method | Path | Request | Response | Lỗi (code) |
|---|---|---|---|---|
| GET | `/v1/events` | Query `since?: int`, `works?: string` (danh sách `work_id` cách nhau dấu phẩy, tối đa 20), `previews?: 0\|1` (mặc định 1); header `Last-Event-ID?` (ưu tiên hơn `since`) | `text/event-stream`; mỗi event: `id: <seq>` (trừ `token.delta`), `event: <type>`, `data: <EventEnvelope JSON>`; ping comment mỗi 15 giây | `UNAUTHORIZED`, `VALIDATION` (works quá 20, since âm) |
| GET | `/v1/jobs/{id}/events` | `since?`, `Last-Event-ID?` | Như trên, chỉ event có `job_id = id`; `token.delta` của job luôn gửi đầy đủ | `NOT_FOUND`, `UNAUTHORIZED` |

Xuất OpenAPI chạy bằng tool, không có route công khai; `/docs` và `/openapi.json` chỉ bật khi `dev_features`.

## Logic xử lý

### A. Quy ước API (áp cho mọi tính năng)

1. **Prefix và xác thực**: mọi route dưới `/v1`, header `Authorization: Bearer <token>` (F00). JSON body/response dùng `snake_case`; FE dùng nguyên tên từ generated types, không đổi sang camelCase.
2. **ID**: chuỗi UUIDv7 (`core/ids.py`), sắp xếp được theo thời gian tạo. **Thời gian**: ISO 8601 UTC `2026-10-02T03:04:05.123Z`. Ngày theo timezone cấu hình (ngân sách) do F04/F12 xử lý.
3. **Phân trang**: `?limit=` (mặc định 50, tối đa 200) và `?cursor=`; response `Page[T] = {items: T[], next_cursor: string | null}`. Cursor = base64url của JSON `{"k": <khóa sắp xếp cuối>, "id": <id cuối>}`, coi là opaque với FE; cursor hỏng → `VALIDATION` (`detail.field = "cursor"`). Không dùng offset cho danh sách lớn (chương, job, event).
4. **Kiểm soát đồng thời**: tài nguyên sửa được có trường `revision: int` tăng mỗi lần ghi. `PATCH`/`PUT` bắt buộc `expected_revision` trong body; khác `revision` hiện tại → 409 `REVISION_CONFLICT`, `detail = {resource, id, expected_revision, current_revision, current?}` (kèm bản hiện tại khi nhỏ để FE dựng diff). Chương dùng `expected_revision` theo định nghĩa của F07 (Plan §7 "expected_revision bắt buộc").
5. **Tác vụ dài**: trả `202 {job_id, status}` + header `Location: /v1/jobs/{id}` ngay sau khi persist job (Plan §4.3, mục tiêu p95 ~300 ms là tiêu chí cần đo, Plan §4.4).
6. **Idempotency**: header `Idempotency-Key` (UUID do FE sinh mỗi thao tác người dùng). Bắt buộc với POST tạo job (`/v1/jobs`, `/v1/works/{id}/autowrite`, `/v1/exports`, `/v1/backups`, `/v1/works/{id}/resync`); khuyến nghị với POST tạo tài nguyên khác. Xử lý: `request_hash = sha256(method + path + canonical JSON body)`.
   - Tạo job: tìm `jobs.idempotency_key`; trùng key + trùng hash → trả lại job cũ (cùng status code); trùng key khác hash → 409 `IDEMPOTENCY_CONFLICT`.
   - POST khác: tra `idempotency_records`; có và chưa hết hạn → trả lại `status_code` + `response_json` đã lưu; ghi bản ghi trong **cùng transaction** với thay đổi nghiệp vụ (qua `unit_of_work` F02). Hết hạn sau 24 giờ (giả định); retention F02 dọn.
7. **Request ID**: mọi response có `X-Request-Id`; log ghi kèm; `ErrorResponse.request_id` giúp đối chiếu log khi người dùng báo lỗi.

### B. Hợp đồng lỗi (Plan §23.1.D)

`ErrorResponse = {code: ErrorCode, message: str, detail: object | null, retryable: bool, action: ErrorAction | null, request_id: str}`. Không trả stack trace. `message` tiếng Việt lấy từ bảng thông điệp BE theo `code` (bản dự phòng); FE hiển thị theo khóa i18n của `code`.

| `code` | HTTP | `retryable` | `action` mặc định | Dùng khi |
|---|---|---|---|---|
| `VALIDATION` | 422 | false | — | Body/query sai; `detail.fields = [{loc, msg, type}]` (chuyển từ `RequestValidationError`) |
| `REVISION_CONFLICT` | 409 | false | `view_diff` | `expected_revision` lệch |
| `WORK_BLOCKED` | 409 | false | `open_resync` | Ghi/enqueue viết khi `continuity_status = blocked_needs_resync`/`stale_from` |
| `WORK_BUSY_QUEUED` | — (không phải lỗi HTTP) | — | `wait` | `wait_reason` của job khi truyện đang có job ghi khác |
| `CHAPTER_RANGE_CONFLICT` | 409 | false | — | Chèn/xóa/sắp xếp chương khi truyện đang chạy (§23.2 #4) |
| `VAULT_LOCKED` | 423 | true | `unlock_vault` | Lời gọi đồng bộ cần key khi vault khóa; cũng là `wait_reason` |
| `PROVIDER_AUTH` | 502 | false | `open_provider_settings` | Provider trả 401/403 |
| `PROVIDER_UNREACHABLE` | 503 | true | `retry` | Mất mạng/timeout tới provider; cũng là `wait_reason` |
| `PROVIDER_RATE_LIMIT` | 429 | true | `wait` | 429 từ provider; header `Retry-After` |
| `PROVIDER_REFUSAL` | 422 | false | `edit_instruction` | Model từ chối |
| `OUTPUT_TRUNCATED` | 422 | true | `retry` | Cắt `max_tokens` sau khi đã thử viết tiếp |
| `STRUCTURED_OUTPUT_INVALID` | 422 | true | `change_model` | JSON sai sau một lần sửa |
| `BUDGET_EXCEEDED` | 409 | false | `adjust_budget` | Vượt ngân sách; cũng là `wait_reason` |
| `UNAUTHORIZED` | 401 | false | `reload` | Token sai (F00) |
| `FORBIDDEN_HOST` / `FORBIDDEN_ORIGIN` | 400 / 403 | false | — | F00 |
| `NOT_FOUND` | 404 | false | — | Không có tài nguyên |
| `IDEMPOTENCY_CONFLICT` | 409 | false | — | Key dùng lại với nội dung khác |
| `DB_BUSY` | 503 | true | `retry` | Writer queue quá hạn (F02) |
| `BACKEND_SHUTTING_DOWN` | 503 | false | — | Đang tắt (F00) |
| `INTERNAL` | 500 | false | `reload` | Lỗi không lường trước; chỉ `request_id` trong detail |

`ErrorAction ∈ retry | reload | wait | view_diff | open_resync | unlock_vault | open_provider_settings | edit_instruction | change_model | adjust_budget`. Tính năng sau được thêm `code` mới nhưng phải đăng ký vào `ErrorCode` và bảng này.

### C. Luồng sự kiện toàn cục (Plan §23.1.C)

Envelope (`api/events_schema.py`, `v = 1`):

```text
EventEnvelope = {v: 1, seq: int, ts: str, type: EventType, work_id?: str, job_id?: str, chapter_no?: int, payload: <theo type>}
EventType = job.queued | job.state | job.step | token.delta | candidate.ready | finding.added
          | chapter.committed | work.continuity | queue.changed | provider.status
          | usage.updated | vault.status | backend.notice
```

1. **Phát**: code nghiệp vụ gọi `uow.add_event(type, payload, work_id, job_id, chapter_no)` trong transaction ghi (F02); bản ghi `job_events` được insert cùng transaction (outbox), sau commit `EventBus.broadcast(rows)`. Event không gắn thay đổi DB (ví dụ `provider.status`) dùng `EventBus.publish_persisted()` — tự đi qua writer queue. Như vậy event đã phát luôn tương ứng dữ liệu đã commit.
2. **`token.delta`** (không lưu): `ProgressSink.on_token` đẩy vào buffer theo `(job_id, candidate_id)`; flush mỗi `token_flush_ms = 75` (trong khoảng 50–100 ms của Plan §4.4) hoặc khi buffer > 4 KB. Payload `{candidate_id, step, offset, text, mode: "full"}` — `offset` là vị trí ký tự (code point) của `text` trong văn bản candidate, giúp FE nối lại không lặp. `seq` = watermark (seq đã lưu lớn nhất), không có dòng `id:`.
3. **Preview cho Phòng viết**: mỗi job đang stream, tối đa mỗi 250 ms (giả định, ~4 lần/giây theo UI §5.3) phát `token.delta` `{candidate_id, step, mode: "preview", tail: <≤ 200 ký tự cuối>}` cho client có `previews=1` và **không** đăng ký work đó.
4. **Kết nối mới** (`api/streams.py`):
   1. `cursor = Last-Event-ID ?? since ?? <watermark hiện tại>` (không có cả hai → chỉ nhận event mới).
   2. Đăng ký subscriber với `EventBus` **trước** (queue có giới hạn `subscriber_queue_max = 1000`, giả định), ghi nhận `watermark_at_subscribe`.
   3. Nếu `cursor < min(seq)` còn giữ, hoặc số event cần replay > `replay_max = 5000` (giả định) → gửi `backend.notice {kind: "replay_gap", oldest_seq, latest_seq}` rồi nhảy tới watermark.
   4. Replay từ DB: `SELECT … WHERE seq > cursor AND seq <= watermark_at_subscribe ORDER BY seq` theo trang 500.
   5. Rút queue live, bỏ event có `seq <= last_sent_seq` (chống trùng giữa replay và live).
   6. Lọc: event đã lưu gửi cho mọi client; `token.delta mode=full` chỉ khi `work_id ∈ works`; `mode=preview` theo quy tắc mục 3.
5. **Backpressure**: `put_nowait` vào queue subscriber thất bại → đánh dấu subscriber "lagging", đóng stream. Client nối lại bằng `Last-Event-ID` và nhận lại từ DB; `token.delta` bị mất trong khoảng đó được FE bù bằng cách đọc candidate partial (F11).
6. **Ping**: dùng ping 15 giây của `EventSourceResponse`; FE coi > 45 giây không có byte nào là kết nối chết.
7. **Shutdown**: phát `backend.notice {kind: "shutting_down"}` rồi đóng mọi stream.
8. **Retention**: xóa `job_events` có `ts` > 90 ngày (Plan §23.2 #10) bằng job retention của F02, theo lô.

Payload tối thiểu do F01 chốt (tính năng phát ra có thể thêm trường, không đổi nghĩa trường có sẵn; đổi nghĩa → tăng `v`):

| `type` | Payload tối thiểu |
|---|---|
| `job.queued` | `{job_type, priority, queue_position}` |
| `job.state` | `{status, wait_reason?: ErrorCode, error?: ErrorResponse, retry_at?}` (`status` theo Plan §4.3) |
| `job.step` | `{step, attempt, round?, max_rounds?, progress?: 0..1}` |
| `token.delta` | `{candidate_id, step, mode: "full" \| "preview", offset?, text?, tail?}` |
| `backend.notice` | `{kind: "replay_gap" \| "shutting_down" \| "jobs_interrupted" \| "migration_done", detail}` |
| `vault.status` | `{state: "absent" \| "locked" \| "unlocked", mode}` (F03) |
| Các type còn lại | Do F10/F11/F12/F04/F14 định nghĩa; phải là model Pydantic trong `events_schema.py` |

### D. OpenAPI → TypeScript

1. `create_app(None)` dựng router đầy đủ nhưng không side effect; `custom_openapi()` đặt `operationId = route.name` (hàm `generate_unique_id_function`), chèn `EventEnvelope` và từng payload vào `components.schemas` bằng `TypeAdapter(EventEnvelope).json_schema(ref_template="#/components/schemas/{model}")`, và `ErrorResponse` làm response mặc định 4xx/5xx của mọi route.
2. `tools/contracts/export_openapi.py` ghi `contracts/openapi.json` ổn định (sort keys).
3. FE script `gen:api` = `openapi-typescript ../contracts/openapi.json -o src/shared/api/generated/schema.d.ts` (file có banner "generated – không sửa tay").
4. CI: `check_contracts.py` fail khi diff khác rỗng; snapshot test cùng nội dung.

## Job và sự kiện phát ra

F01 tự phát: `backend.notice` (`replay_gap`, `shutting_down`). Các type khác do tính năng nghiệp vụ phát qua cơ chế ở mục C.

## Lỗi và trường hợp biên

| Tình huống | Xử lý | Mã lỗi |
|---|---|---|
| `Last-Event-ID` không phải số | Bỏ qua, coi như không có; log cảnh báo | — |
| `since` lớn hơn watermark (DB đã restore về bản cũ) | Gửi `replay_gap` để FE làm mới toàn bộ | — |
| Client chậm, queue đầy | Đóng stream, client tự replay | — |
| Writer queue lỗi khi lưu event | Transaction nghiệp vụ cùng rollback; không broadcast | `DB_BUSY` hoặc `INTERNAL` |
| Exception không bắt trong route | 500 với `request_id`, log đầy đủ (che secret) | `INTERNAL` |
| Exception trong generator SSE | Gửi `backend.notice {kind:"stream_error"}` rồi đóng; client nối lại | — |
| `works` chứa work không tồn tại | Bỏ qua phần tử đó (không lỗi) | — |
| Hai request cùng `Idempotency-Key` đến đồng thời | Unique constraint; request thua chờ và trả bản đã lưu | — |

## Việc cần làm

- [ ] `core/ids.py`, `core/clock.py`, `core/errors.py` (`ErrorCode`, `ErrorAction`).
- [ ] `api/errors.py` + handler cho `AppError`, `RequestValidationError`, `HTTPException`, `Exception`.
- [ ] `api/conventions.py` (`Page[T]`, cursor), `api/request_id.py`, `api/idempotency.py`.
- [ ] `api/events_schema.py` với union theo `type`; `api/openapi.py`.
- [ ] `jobs/events.py` (`EventBus`: chế độ RAM cho R0, chế độ DB cho R1), flush `token.delta`, preview.
- [ ] `api/streams.py` với `EventSourceResponse` (đối chiếu docs FastAPI ≥ 0.135 cho tên API).
- [ ] Định nghĩa `job_events`, `idempotency_records` trong migration baseline F02; repository `job_events.py`.
- [ ] `infrastructure/ai/progress_adapter.py` triển khai `ProgressSink` (ai.md).
- [ ] `tools/contracts/export_openapi.py`, `check_contracts.py`; job CI.
- [ ] `contracts/examples/` cho lỗi và từng event type.

## Test

| Loại | Nội dung | File dự kiến |
|---|---|---|
| unit | Cursor encode/decode, cursor hỏng → `VALIDATION` | `be/tests/unit/api/test_conventions.py` |
| unit | Mapping exception → `ErrorResponse` cho từng `ErrorCode`; không lộ stack trace | `be/tests/unit/api/test_errors.py` |
| unit | `EventBus`: subscribe-trước-replay không trùng/không sót; queue đầy → đóng subscriber; flush token theo thời gian và kích thước | `be/tests/unit/jobs/test_event_bus.py` |
| contract | Snapshot `contracts/openapi.json`; mọi route khai báo `ErrorResponse`; `EventEnvelope` có trong components | `be/tests/contract/test_openapi_snapshot.py` |
| contract | Ví dụ trong `contracts/examples/*.json` validate với model | `be/tests/contract/test_examples.py` |
| integration | SSE: replay theo `since` và `Last-Event-ID`; `replay_gap` khi since quá cũ; lọc `works=`; preview; event chỉ phát sau commit (rollback → không có event) | `be/tests/integration/test_events_sse.py` |
| integration | Idempotency: lặp key trả cùng kết quả; khác body → 409; tạo job song song cùng key → một job | `be/tests/integration/test_idempotency.py` |

## Tên mới đề xuất

- Bảng `idempotency_records` (các cột ở trên). Cột của `job_events`: `seq`, `v`, `ts`, `type`, `work_id`, `job_id`, `chapter_no`, `payload_json` (Plan §5 chỉ nêu tên bảng).
- File: `core/ids.py`, `core/clock.py`, `core/errors.py`, `api/conventions.py`, `api/idempotency.py`, `api/request_id.py`, `api/events_schema.py`, `api/openapi.py`, `tools/contracts/export_openapi.py`, `tools/contracts/check_contracts.py`, repository `job_events.py`.
- Kiểu: `ErrorResponse`, `ErrorCode`, `ErrorAction`, `AppError`, `Page[T]`, `EventEnvelope`, `EventBus`, `EVENT_SCHEMA_VERSION`.
- Mã lỗi bổ sung ngoài Plan §23.1.D: `UNAUTHORIZED`, `FORBIDDEN_HOST`, `FORBIDDEN_ORIGIN`, `NOT_FOUND`, `IDEMPOTENCY_CONFLICT`, `DB_BUSY`, `BACKEND_SHUTTING_DOWN`, `INTERNAL`. Trường `request_id` trong envelope lỗi. Giá trị `ErrorAction` liệt kê ở mục B.
- Header `Idempotency-Key`, `X-Request-Id`; query `previews` của `/v1/events`.
- `backend.notice` kind: `replay_gap`, `shutting_down`, `jobs_interrupted`, `migration_done`, `stream_error`. `token.delta` trường `mode`, `offset`, `tail`.
- Tham số cấu hình: `token_flush_ms`, `subscriber_queue_max`, `replay_max`.
