# F14 — Backend

## Module và file

```text
be/src/writestory_be/modules/operations/
  notifications/  router.py schemas.py service.py   outbox, đọc/đánh dấu, cài đặt
  usage/          router.py schemas.py service.py   tính giá, ghi records/counters, tổng hợp
  logs/           router.py schemas.py service.py   đọc log hệ thống, log AI debug
  storage/        router.py schemas.py service.py   đo dung lượng, dọn dẹp theo chính sách
be/src/writestory_be/infrastructure/
  ai/progress_adapter.py     nhận Usage/RequestTrace từ AI → usage service / ai_debug_log
  logging/setup.py           JSON lines, xoay vòng, bộ lọc che secret (redaction.py)
  logging/redaction.py
  logging/ai_debug_log.py    ghi data/logs/ai/, giới hạn dung lượng
be/src/writestory_be/jobs/handlers/cleanup.py   job dọn dẹp định kỳ
```

## Dữ liệu và migration

| Bảng | Cột chính | Ràng buộc / index | Ghi chú |
|---|---|---|---|
| `notification_outbox` | `id`, `type`, `severity` (`info`/`warning`/`error`), `work_id`, `job_id`, `chapter_no`, `title_key`, `body_params` JSON, `target_route`, `dedupe_key`, `created_at`, `read_at`, `native_status` (`pending`/`sent`/`skipped`/`failed`), `native_attempts`, `native_sent_at`, `expires_at` | idx (`read_at`, `created_at`), unique (`dedupe_key`) | Plan §18; ghi cùng transaction với thay đổi trạng thái gây ra nó |
| `usage_records` | `id`, `ts`, `job_id`, `step_id`, `work_id`, `provider_id`, `model_id`, `role`, `attempt`, `reported`, `input_tokens`, `output_tokens`, `reasoning_tokens`, `cache_read_tokens`, `cache_write_tokens`, `cache_write_ttl`, `cost_usd_micros` (null nếu thiếu giá), `price_snapshot` JSON, `stop_reason`, `partial`, `latency_ms`, `error_code`, `day` (ngày theo timezone) | idx (`ts`), idx (`work_id`, `day`), idx (`provider_id`, `day`) | Một dòng/request AI |
| `usage_counters` | `day`, `scope_type` (`app`/`work`/`provider`/`model`), `scope_id`, `requests`, `input_tokens`, `output_tokens`, `cache_read_tokens`, `cache_write_tokens`, `cost_usd_micros`, `unpriced_requests`, `rate_limited`, `errors`, `updated_at` | PK (`day`, `scope_type`, `scope_id`) | Plan §5; F12 đọc để kiểm ngân sách |
| `settings` (khóa) | `notifications.native_enabled`=true, `notifications.types` JSON, `debug.ai_log_enabled`=false, `debug.ai_log_max_file_bytes`=2 MiB, `debug.ai_log_max_total_bytes`=500 MiB, `power.keep_awake_while_writing`=true, `retention.*` | — | Giá trị dung lượng là giả định |

Tiền lưu số nguyên micro-USD (giá provider theo USD/1M token, giả định đơn vị USD). `day` tính bằng `budget.timezone` tại thời điểm ghi; đổi timezone không ghi lại ngày cũ.

Migration: `be/migrations/versions/<rev>_f14_usage_notifications.py`. Không backfill.

## API

| Method | Path | Request | Response | Lỗi (code) |
|---|---|---|---|---|
| GET | `/v1/notifications?unread=&cursor=` | — | `{items[], unread_count, next_cursor}` | — |
| POST | `/v1/notifications/{id}/read` | — | 204 | `NOT_FOUND` |
| POST | `/v1/notifications/read-all` | — | 204 | — |
| POST | `/v1/notifications/{id}/native` | `{status: "sent" \| "failed" \| "skipped"}` | 204 | `NOT_FOUND` |
| GET/PUT | `/v1/settings/notifications` | `{native_enabled, types: {chapter_blocked: bool, …}}` | settings | `VALIDATION` |
| GET | `/v1/usage/summary?from=&to=&group_by=hour\|day\|work\|model\|provider&work_id=` | — | `{buckets: [{key, requests, input_tokens, output_tokens, cache_read_tokens, cache_write_tokens, cost_usd, unpriced_requests}], totals, cache_hit_ratio}` | `VALIDATION` |
| GET | `/v1/usage/records?work_id=&job_id=&cursor=` | — | `{items[], next_cursor}` | — |
| GET | `/v1/providers/{id}/usage` | — | `{today: {requests, rpm_now, tpm_now, cost_usd, cache_hit_ratio}, limits}` | `NOT_FOUND` (Plan §7) |
| GET | `/v1/logs?level=&source=backend\|desktop&cursor=` | — | `{lines: [{ts, level, logger, msg, fields}], next_cursor}` | — |
| GET | `/v1/logs/ai?job_id=` | — | `[{job_id, step, attempt, file_relpath, size, ts}]` | — |
| GET | `/v1/logs/ai/{job_id}/{name}` | — | nội dung JSON (đã che) | `NOT_FOUND` |
| GET | `/v1/storage` | — | `{data_root, disk_free_bytes, categories: [{key, bytes, files}], db_tables: [{name, bytes, rows, estimated}], reclaimable: [{target, bytes, items}]}` | — |
| POST | `/v1/storage/cleanup` | `{targets: [...], dry_run}` | `{freed_bytes, deleted: {target: count}}` hoặc 202 `{job_id}` khi lớn | `MAINTENANCE`, `VALIDATION` |

`categories.key`: `db`, `db_wal`, `assets`, `imports`, `methods`, `exports`, `backups`, `logs`, `logs_ai`, `cache`, `tmp`. `targets`: `rejected_candidates`, `superseded_candidates`, `job_events`, `traces`, `logs`, `ai_logs`, `tmp`, `cache`, `old_exports`, `old_backups`, `vacuum`.

## Logic xử lý

**Usage** (Plan §4.3, §6.5): `progress_adapter.on_usage(usage)` → `usage.service.record()`:

1. Giá: đọc `provider_models` của `model_id` (giá/1M token vào, ra, đọc cache, ghi cache); snapshot vào `price_snapshot`.
2. `cost = in·p_in + out·p_out + cache_read·p_cache_read + cache_write·p_cache_write` (chia 1.000.000, làm tròn micro-USD). Thiếu bất kỳ giá cần dùng → `cost_usd_micros = null`, `unpriced_requests++`. `reported=false` → không cộng token, chỉ cộng `requests`.
3. Một transaction qua writer queue: insert `usage_records`; upsert 4 dòng `usage_counters` (app, work, provider, model); cộng `jobs.usage`/`job_steps.usage`.
4. Phát `usage.updated` gộp tối đa 1 lần/giây/truyện: `{work_id, cost_today, tokens_today, app_cost_today}`.

`cache_hit_ratio = cache_read / (input + cache_read)` trên khoảng thời gian chọn (Review §6).

**Thông báo** (Plan §23.2 #12, FL24 bước 4):

| `type` | Nguồn | Mức |
|---|---|---|
| `chapter_blocked` | Job → `waiting_user`/`blocked` hoặc continuity → `blocked_needs_resync` | error |
| `batch_completed` | Batch auto-write `completed` | info |
| `provider_error_persistent` | `PROVIDER_UNREACHABLE` hoặc 5xx liên tục > 5 phút (giả định), hoặc `PROVIDER_AUTH` ngay | error |
| `budget_exhausted` | Lần đầu trong ngày job vào `BUDGET_EXCEEDED` | warning |
| `jobs_interrupted` | Reconcile khi khởi động có job `interrupted` | warning |
| `backup_done` / `restore_done` / `export_done` | Job F13 xong | info |

- Ghi outbox trong cùng transaction với thay đổi trạng thái (outbox pattern); `dedupe_key` (ví dụ `chapter_blocked:<work>:<chapter>`) chặn trùng.
- Phát event `notification.created`. BE không gọi Tauri được: FE nhận event, gửi native qua plugin rồi báo `POST …/native`. Lúc FE kết nối lại, lấy `native_status=pending` tạo trong 1 giờ gần nhất (giả định) để gửi bù; cũ hơn → `skipped`.
- Lỗi gửi native chỉ cập nhật `native_status=failed`; không ảnh hưởng chương đã commit (FL24, §21).

**Log** (Plan §3.1): JSON lines `data/logs/backend.log`, xoay vòng 10 MiB × 5 file (giả định). Bộ lọc `redaction.py` áp cho mọi record: header `Authorization`/`x-api-key`, chuỗi giống khóa (`sk-…`, `sk-ant-…`, dạng Bearer), mật khẩu vault, token phiên backend, userinfo trong URL → `«đã che»`. Không log nội dung chương ở mức INFO.

**Log debug AI** (Plan §23.2 #11): chỉ khi `debug.ai_log_enabled`; runner đặt `debug_trace=True` vào `GenerationInput`. `ai_debug_log.write(trace)` → `data/logs/ai/<YYYY-MM-DD>/<job_id>/<step_no>-<stage>-<attempt>.json`; chạy redaction trên toàn bộ chuỗi; file > `max_file_bytes` → cắt phần giữa của messages kèm đánh dấu `…[đã cắt N ký tự]…`; tổng thư mục > `max_total_bytes` → xóa thư mục ngày cũ nhất. Ghi bằng `asyncio.to_thread`, lỗi ghi chỉ log cảnh báo.

**Lưu trữ và dọn dẹp** (Plan §23.2 #10):

| Đối tượng | Chính sách mặc định |
|---|---|
| `chapter_revisions` đã commit | Giữ tất cả, không bao giờ dọn |
| Candidate `rejected`/`superseded`/`partial` | 30 ngày (`expires_at`) |
| `job_events` | 90 ngày |
| Context trace chi tiết | Theo tổng dung lượng tối đa (`retention.traces_max_bytes`, giả định 200 MiB), xóa cũ nhất |
| `usage_records` | 365 ngày (giả định); `usage_counters` giữ vĩnh viễn |
| Log, log AI | Xoay vòng/giới hạn như trên |
| `tmp/` | File > 24 giờ và không thuộc job đang chạy |
| Export/backup | Chỉ khi người dùng chọn; backup theo retention F13 |

- Job `cleanup` chạy khi khởi động và mỗi 24 giờ (tác vụ phụ, không khóa truyện); xóa theo lô nhỏ qua writer queue.
- `vacuum`: chỉ khi không có job đang chạy; dùng chế độ bảo trì F13 vì VACUUM chặn ghi. Nếu DB tạo với `auto_vacuum=INCREMENTAL` (F02 quyết định) thì dùng `PRAGMA incremental_vacuum` không cần bảo trì.
- Dung lượng bảng: dùng `dbstat` nếu có; không có → `rows × độ dài trung bình`, `estimated=true`. `disk_free_bytes` bằng `shutil.disk_usage(data_root)`.

**Giữ máy thức** (Plan §23.2 #9): BE chỉ phát `queue.changed.summary.running`; FE gọi Rust (fe.md). Khi máy thức dậy, request treo hết timeout và job chạy lại từ checkpoint (F12).

## Job và sự kiện phát ra

| Event `type` | Khi nào | Payload |
|---|---|---|
| `usage.updated` | Sau ghi usage (gộp 1 s) | `{work_id, cost_today, tokens_today, app_cost_today}` |
| `notification.created` | Insert outbox | `{id, type, severity, title_key, body_params, target_route, native: bool}` |
| `job.state` / `job.step` | Job `cleanup` | `{stage, done, total}` |

## Lỗi và trường hợp biên

| Tình huống | Xử lý | Mã lỗi |
|---|---|---|
| Sửa giá model sau khi đã gọi | Không tính lại lịch sử (giá snapshot) | — |
| Request lỗi không có usage | Dòng `usage_records` `reported=false`, `error_code` | — |
| Hai thông báo cùng chương bị chặn | `dedupe_key` giữ một | — |
| Dọn dẹp khi đang restore | Từ chối | `MAINTENANCE` |
| Thư mục `logs/ai` bị xóa tay | Tự tạo lại | — |
| Ổ đầy khi ghi log debug | Tự tắt log debug, thông báo `backend.notice` | — |

## Việc cần làm

- [ ] Migration 3 bảng + khóa settings.
- [ ] Usage service: giá, records, counters, `usage.updated`.
- [ ] Outbox + API thông báo + gửi bù khi reconnect.
- [ ] Logging JSON + redaction + xoay vòng; API đọc log.
- [ ] `ai_debug_log.py` + giới hạn dung lượng.
- [ ] Storage: đo dung lượng, dọn dẹp, job `cleanup` định kỳ.

## Test

| Loại | Nội dung | File dự kiến |
|---|---|---|
| unit | Công thức chi phí, thiếu giá, `reported=false` | `be/tests/unit/operations/test_usage_cost.py` |
| unit | Redaction: key Anthropic/OpenAI, Bearer, URL userinfo | `be/tests/unit/infrastructure/test_redaction.py` |
| unit | Chính sách giữ: chọn đúng bản ghi cần xóa, không chạm revision | `be/tests/unit/operations/test_retention.py` |
| integration | Đối soát `usage_records` ↔ `usage_counters` sau 3 truyện mock song song | `be/tests/integration/test_usage_counters.py` |
| integration | Chương bị chặn → outbox + event; lỗi native không đổi chương (T17) | `be/tests/integration/test_notifications.py` |
| integration | Log debug bật: file đúng chỗ, không chứa key, tổng ≤ giới hạn (T15) | `be/tests/integration/test_ai_debug_log.py` |

## Tên mới đề xuất

- Bảng `usage_records` (một dòng/request AI); cột `usage_counters.{day, scope_type, scope_id, requests, input_tokens, output_tokens, cache_read_tokens, cache_write_tokens, cost_usd_micros, unpriced_requests, rate_limited, errors}`; cột `notification_outbox.*` như bảng trên.
- Khóa settings `notifications.*`, `debug.ai_log_*`, `power.keep_awake_while_writing`, `retention.*`.
- API `/v1/notifications…`, `/v1/settings/notifications`, `/v1/usage/summary`, `/v1/usage/records`, `/v1/logs`, `/v1/logs/ai…`.
- Event `notification.created`. Job type `cleanup`.
- File `infrastructure/logging/{setup,redaction,ai_debug_log}.py`, module `modules/operations/{notifications,usage,logs,storage}`.
