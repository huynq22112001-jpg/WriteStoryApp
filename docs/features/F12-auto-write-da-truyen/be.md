# F12 — Backend

## Module và file

```text
be/src/writestory_be/
  jobs/
    supervisor.py      Vòng đời task chạy job, cancel, deadline
    scheduler.py       Ready set, xoay vòng có trọng số, cấp worker (R2)
    locks.py           work_locks: acquire/heartbeat/release, lease
    runner.py          Dispatch theo job.type → handler (write F10, revise/resync F11)
    recovery.py        Reconcile sau restart
    budget.py          Kiểm ngân sách ngày/truyện/app theo timezone (đọc usage_counters F14)
    events.py          Phát job.* / queue.changed
  infrastructure/ai/
    limits.py          ProviderLimiter: semaphore, token bucket RPM/TPM, cooldown Retry-After
    model_resolver.py  Ghim model + effort theo vai trò khi job bắt đầu (F04)
  modules/autowrite/
    router.py  schemas.py  service.py  domain.py (tính range, chế độ duyệt, ước tính)
```

## Dữ liệu và migration

| Bảng | Cột chính | Ràng buộc / index | Ghi chú |
|---|---|---|---|
| `work_queues` | `work_id` PK, `autowrite_status` (`idle`/`active`/`paused`/`cancelled`/`completed`), `mode` (`auto`/`review_each`/`review_every_k`), `review_every_k`, `from_chapter_no`, `target_chapter_no`, `chapters_done`, `since_review`, `priority` (thứ tự kéo thả, nhỏ = trước), `weight` (mặc định 1), `current_weight` (SWRR), `pause_reason`, `daily_budget_usd_micros`, `daily_budget_tokens`, `batch_id`, `updated_at` | idx (`autowrite_status`, `priority`) | Plan §5. Ngân sách riêng truyện null = theo mặc định |
| `work_locks` | `work_id` PK, `job_id`, `owner_instance`, `acquired_at`, `heartbeat_at`, `lease_expires_at` | PK đảm bảo 1 khóa/truyện | Plan §4.2 |
| `jobs` (cột F12 dùng) | `id`, `idempotency_key` UNIQUE, `type`, `work_id`, `chapter_no`, `batch_id`, `queue_position`, `priority`, `status`, `waiting_reason`, `waiting_until`, `base_revision_id`, `stage`, `checkpoint` JSON, `progress` JSON, `pinned_config` JSON, `attempt`, `cancel_requested_at`, `error_code`, `usage` JSON, `created_at`, `started_at`, `finished_at` | idx (`work_id`, `status`, `queue_position`), idx (`status`, `waiting_until`) | Plan §4.3 liệt kê trường; bảng thuộc F02 |
| `provider_limits` | `provider_id` PK, `max_concurrent_requests`, `rpm`, `tpm`, `cooldown_until`, `consecutive_failures`, `last_error_code`, `last_error_at`, `updated_at` | — | Mặc định cloud 4, local 1 (Plan §4.2) |
| `settings` (khóa) | `scheduler.worker_pool_size`=4, `scheduler.focus_bonus`=1, `budget.daily_usd_micros`, `budget.daily_tokens`, `budget.timezone`, `budget.per_work_default_usd_micros`, `autowrite.default_mode`, `autowrite.default_k`=5, `autowrite.resume_after_restart`=false | — | UI §5.6.3 |

Loại job ghi (cần `work_locks`): `write`, `revise`, `resync`, `rollback`, `import` (Plan §4.2). Tác vụ phụ không khóa: `review`, `export`, `backup`, `cleanup`.

Migration: `be/migrations/versions/<rev>_f12_queues_locks_limits.py`. Không cần backfill; tạo dòng `work_queues` lười khi truyện bật auto-write lần đầu.

## API

| Method | Path | Request | Response | Lỗi (code) |
|---|---|---|---|---|
| POST | `/v1/works/{id}/autowrite` | `{count?\|target_chapter?, mode, review_every_k?, priority?, confirm_over_budget?, idempotency_key}` | 202 `{batch_id, from_chapter_no, to_chapter_no, first_job_id, estimate}` | `CHAPTER_RANGE_CONFLICT` 409, `WORK_BLOCKED` 409, `AUTOWRITE_ACTIVE` 409, `BUDGET_EXCEEDED` 409 (`action: confirm`), `VALIDATION` 422 |
| POST | `/v1/works/{id}/autowrite/pause` | `{when: "after_chapter" \| "for_edit"}` | `{autowrite_status, stopping_job_id?}` | `NOT_FOUND` |
| POST | `/v1/works/{id}/autowrite/resume` | — | `{autowrite_status, next_job_id?}` | `WORK_BLOCKED`, `VAULT_LOCKED` (chỉ cảnh báo) |
| POST | `/v1/works/{id}/autowrite/cancel` | — | `{autowrite_status: "cancelled", cancelled_job_id?}` | — |
| POST | `/v1/works/{id}/autowrite/estimate` | `{count?\|target_chapter?, mode}` | `{chapters, basis: history\|default, sample_size, tokens: {input, output, cache_read}: {min,max}, cost_usd: {min,max}\|null, duration_s: {min,max}\|null, unpriced_models[], budget: {work_remaining, app_remaining, exceeds}}` | `CHAPTER_RANGE_CONFLICT` |
| GET | `/v1/queues` | — | `{summary: {running, waiting, blocked, pool_size, cost_today, budget_today}, providers: [{id, in_use, max, rpm_used, tpm_used, cooldown_until, status}], works: [{work_id, title, autowrite, current_job: {id, type, chapter_no, status, stage, repair_round, repair_max, waiting_reason, waiting_until}, continuity, cost_today, priority}]}` | — |
| PUT | `/v1/queues/priority` | `{work_ids: [...]}` (thứ tự mới) | `{works: [{work_id, priority}]}` | `VALIDATION` |
| POST | `/v1/jobs/{id}/cancel` | — | `{status}` | `NOT_FOUND` |
| POST | `/v1/jobs/{id}/resume` | — | `{status: "queued"}` | `VALIDATION` (job không ở `interrupted`/`failed`/`waiting_user` resume được) |
| GET/PUT | `/v1/settings/concurrency` | `{worker_pool_size, budget: {...}, timezone}` | settings | `VALIDATION` |

Giới hạn từng provider (`max_concurrent_requests`, RPM, TPM) sửa qua API provider của F04 và lưu `provider_limits`.

## Logic xử lý

**State machine job** (Plan §4.3):

| Từ | Sang | Khi |
|---|---|---|
| — | `queued` | Persist job (API trả ngay, mục tiêu p95 ~300 ms – Plan §4.4, chưa đo) |
| `queued`/`waiting_slot` | `running` | Scheduler admit: worker trống, khóa giành được, provider còn slot, ngân sách, vault mở |
| `queued` | `waiting_slot` | Không admit được → ghi `waiting_reason` (+ `waiting_until` nếu có) |
| `running` | `waiting_slot` | Ở ranh giới bước: hết ngân sách / provider không phản hồi; job giữ khóa và vị trí đầu hàng, nhả worker |
| `running` | `succeeded` / `waiting_user` / `blocked` / `failed` / `cancelled` | Kết quả handler; `blocked` khi truyện chuyển `blocked_needs_resync` |
| `running` | `interrupted` | Reconcile sau crash/đóng app |
| `interrupted`/`failed`/`waiting_user` | `queued` | `resume` (từ checkpoint) |

`waiting_reason`: `WORKER_POOL_FULL`, `PROVIDER_CONCURRENCY_FULL`, `PROVIDER_RATE_LIMIT`, `BUDGET_EXCEEDED`, `WORK_BUSY_QUEUED` (khóa truyện đang bị job khác giữ), `VAULT_LOCKED`, `PROVIDER_UNREACHABLE`, `WORK_PAUSED`.

**Scheduler** (`jobs/scheduler.py`), một task asyncio, đánh thức bằng `asyncio.Event` khi: job mới, job kết thúc, khóa nhả, vault mở, đổi ưu tiên/cài đặt, `waiting_until` gần nhất tới hạn, qua nửa đêm theo timezone. Không có tick chồng nhau vì chỉ một vòng lặp.

```text
loop:
  await wake.wait(timeout = earliest(waiting_until, next_midnight))
  free = pool_size - count(running)
  skipped = {}
  while free > 0:
    R = ready_set() - skipped        # truyện có job đầu hàng đủ điều kiện:
                                     #   autowrite không paused (job thủ công vẫn chạy)
                                     #   continuity ok (write); stale/blocked chỉ cho resync/revise
                                     #   job đầu hàng không có waiting_until ở tương lai
    if R empty: break
    for w in R: w.ew = w.weight + (focus_bonus if w đang mở trên UI else 0)
    for w in R: w.cw += w.ew
    pick = max(R, key=(cw, -priority))          # smooth weighted round-robin
    pick.cw -= sum(w.ew for w in R)
    job = head(pick)
    ok, reason, until = admit(job)   # khóa → vault → ngân sách → provider slot (theo provider của bước kế tiếp)
    if not ok: set_waiting(job, reason, until); skipped.add(pick); continue
    supervisor.start(job); free -= 1
  persist current_weight; emit queue.changed (gộp, tối đa 4 lần/giây)
```

- Không bao giờ lấy N truyện đầu danh sách (khác InkOS `slice(0, N)`); trọng số ≥ 1 nên không truyện nào bị bỏ đói (Plan §4.2).
- "Truyện đang mở" lấy từ tham số `works=` của kết nối `/v1/events` hiện hành (giả định thiết kế).
- Đổi `worker_pool_size` lúc chạy: tăng → wake; giảm → không ngắt job, chỉ ngừng admit.

**Khóa truyện** (`jobs/locks.py`): `INSERT … ON CONFLICT DO NOTHING` vào `work_locks`; lease 60 s, heartbeat 20 s bởi supervisor (giả định). Job đang `waiting_slot` sau khi đã chạy vẫn giữ khóa (scheduler gia hạn) để job thủ công khác không chen vào giữa chương. Lease hết hạn với `owner_instance` khác → coi như mồ côi, giải phóng.

**Provider limiter** (`infrastructure/ai/limits.py`, BE sở hữu, inject vào adapter AI qua port – xem ai.md):

- `acquire(provider_id, model_id, est_input_tokens, max_tokens)`: chờ `cooldown_until`; semaphore provider (`max_concurrent_requests`) lồng semaphore model (giới hạn đồng thời riêng trong `provider_models`); bucket RPM (dung lượng `rpm`, nạp `rpm/60` mỗi giây); bucket TPM giữ chỗ `est_input + max_tokens`, hoàn lại phần dư theo usage thực khi `release`.
- `report(provider_id, status, retry_after_s)`: 429 → `cooldown_until = now + Retry-After` (không có header: backoff); 5xx/timeout → `consecutive_failures++`.
- Retry transport tối đa 3 lần, `delay = min(60, 2·2^attempt)` + full jitter, ưu tiên `Retry-After`; không retry 401/403/404 model-not-found (do policy AI thực hiện, limiter cung cấp cooldown dùng chung).
- Hết retry do mất kết nối → job `waiting_slot` `PROVIDER_UNREACHABLE`, `waiting_until` theo 15 s, 30 s, 60 s, … tối đa 5 phút (Plan §23.2 #8); resume từ checkpoint bước.
- 401/403 → job `failed` `PROVIDER_AUTH`, batch `paused` (`pause_reason = PROVIDER_AUTH`).

**Ngân sách** (`jobs/budget.py`): ngày = ngày lịch theo `budget.timezone` (khác InkOS dùng UTC trong RAM, Plan §14.2). Kiểm trước admit và ở mỗi ranh giới bước: `spent(app) < budget_app` và `spent(work) < budget_work` (token và chi phí; bộ đếm `usage_counters` của F14). Vượt → `waiting_slot` `BUDGET_EXCEEDED`, `waiting_until = nửa đêm kế tiếp`. Không cắt giữa một request đang stream.

**Autowrite** (FL05): tính range: `from = chương committed mới nhất + 1`; `target_chapter` ≤ mới nhất hoặc range không bắt đầu ở chương kế → `CHAPTER_RANGE_CONFLICT`. Chỉ tạo job `write` cho chương `from`; sau mỗi commit (hook từ F10) tạo job chương kế nếu: `autowrite_status = active`, chưa tới target, `continuity_status = ok`, và chế độ cho phép:

| Chế độ | Sau khi chương N qua mọi cổng |
|---|---|
| `auto` | Commit, enqueue N+1; rơi vào `waiting_user` → batch `paused` |
| `review_each` | Job `waiting_user` với candidate `ready`; N+1 chỉ tạo khi tác giả accept (F11) |
| `review_every_k` | Như `auto`; `since_review` đạt K → chương thứ K dừng `waiting_user` |

`pause after_chapter`: đặt `paused`, job hiện tại chạy xong. `pause for_edit` (Plan §23.2 #3): yêu cầu cancel ở ranh giới bước kế; candidate của chương đang viết → `superseded`; editor chương N-1 mở khóa khi job dừng. `cancel`: cancel job hiện tại, batch `cancelled`, chương đã commit giữ nguyên.

**Sửa tay khi đang chạy** (Plan §23.2 #3): `PUT /v1/chapters/{id}/working-copy` lên chương N-1 khi job `write` N đang chạy → `409 CHAPTER_IS_BASE`. Sửa chương K < N-1 → F11 đặt `stale_from(K)`; scheduler không tạo job chương N+1 (batch tự `paused`, `pause_reason = STALE`).

**Ước tính** (Plan §23.2 #6): lấy usage của tối đa 10 chương committed gần nhất (tổng mọi bước, kể cả vòng sửa); ≥ 3 mẫu → `basis = history`, min/max = min/max mẫu × số chương; ít hơn → `basis = default` từ độ dài mục tiêu × tỷ lệ token/âm tiết của model (giả định nếu chưa đo) × hệ số bước cấu hình. Giá từ `provider_models` theo `role_models` đã phân giải; model thiếu giá → `unpriced_models`, `cost_usd = null`. Thời gian từ thời lượng job lịch sử; không có thì `null`. Truyện chạy tuần tự nên không chia cho số worker.

**Reconcile khi khởi động** (`jobs/recovery.py`, FL01 bước 3): `running` → `interrupted`; candidate `streaming` → `partial`; xóa `work_locks` của instance cũ; batch `active` → `paused` (`pause_reason = INTERRUPTED`) trừ khi `autowrite.resume_after_restart = true`. Resume chạy lại từ bước hợp lệ cuối của checkpoint; bước Write dở chạy lại từ đầu (không resume từng token, Plan §4.3).

Quy tắc transaction: chuyển trạng thái job, khóa, `work_queues` mỗi lần một transaction ngắn qua writer queue; không giữ transaction khi chờ limiter hay AI.

## Job và sự kiện phát ra

| Event `type` | Khi nào | Payload |
|---|---|---|
| `job.queued` | Job persist | `{job_id, type, chapter_no, queue_position}` |
| `job.state` | Đổi `status` | `{job_id, status, waiting_reason?, waiting_until?, error_code?}` |
| `job.step` | Đổi bước/vòng sửa | `{job_id, stage, repair_round?, repair_max?, wait?: {reason, until}}` |
| `stream.tail` | Mỗi ~250 ms khi đang Write | `{job_id, tail: ≤ 2 dòng cuối}` (không lưu `job_events`) |
| `queue.changed` | Đổi ready set/ưu tiên/autowrite | `{summary, works_changed: [...]}` |
| `provider.status` | Slot/cooldown/lỗi đổi | `{provider_id, in_use, max, cooldown_until, status}` |

## Lỗi và trường hợp biên

| Tình huống | Xử lý | Mã lỗi |
|---|---|---|
| Gửi autowrite trùng `idempotency_key` | Trả batch cũ | — |
| Bật autowrite khi đang `active` | Từ chối | `AUTOWRITE_ACTIVE` |
| Truyện `blocked_needs_resync`/`stale_from` | Từ chối bắt đầu | `WORK_BLOCKED` |
| Ước tính vượt ngân sách, chưa `confirm_over_budget` | 409 kèm ước tính | `BUDGET_EXCEEDED` |
| Job thủ công (revise) chờ sau job write đang chạy | `waiting_slot` | `WORK_BUSY_QUEUED` |
| Đổi model/effort khi batch chạy | Áp từ job chương kế (`pinned_config` mới) | — |
| Máy ngủ dậy, request treo | Hết timeout → retry/`PROVIDER_UNREACHABLE` → checkpoint | — |
| Cancel trong lúc commit transaction | Transaction xong trước, cancel áp cho chương kế; cancel ghi nhận trước commit thì chặn commit | — |

## Việc cần làm

- [ ] Migration `work_queues`, `work_locks`, `provider_limits`, cột `jobs` còn thiếu.
- [ ] `locks.py` + test lease mồ côi.
- [ ] `scheduler.py` SWRR + admit + wake events.
- [ ] `limits.py` semaphore/bucket/cooldown + port cho AI.
- [ ] `budget.py` theo timezone + đánh thức nửa đêm.
- [ ] `modules/autowrite` API, chế độ duyệt, hook sau commit, estimate.
- [ ] `recovery.py` reconcile.
- [ ] Throttle `stream.tail`, `queue.changed`.

## Test

| Loại | Nội dung | File dự kiến |
|---|---|---|
| unit | SWRR: 5 truyện trọng số khác nhau, không bỏ đói; tie-break theo `priority` | `be/tests/unit/jobs/test_scheduler_fairness.py` |
| unit | Token bucket RPM/TPM, hoàn token dư, cooldown `Retry-After` | `be/tests/unit/infrastructure/test_limits.py` |
| unit | Ngày ngân sách theo timezone (Asia/Ho_Chi_Minh, đổi múi) | `be/tests/unit/jobs/test_budget.py` |
| unit | Bảng chuyển trạng thái job hợp lệ/cấm | `be/tests/unit/jobs/test_job_states.py` |
| integration | 5 truyện mock song song, pool 4, provider max 3, không `database is locked` (T08) | `be/tests/integration/test_multi_work.py` |
| integration | 3 chế độ autowrite trên 1 truyện (T07) | `be/tests/integration/test_autowrite_modes.py` |
| integration | Kill giữa bước → interrupted → resume (T09) | `tests/integration/test_crash_resume.py` |
| integration | 429/401/mất mạng/vault khóa (T15) | `be/tests/integration/test_provider_waits.py` |

## Tên mới đề xuất

- Cột: `work_queues.{autowrite_status, mode, review_every_k, from_chapter_no, target_chapter_no, chapters_done, since_review, priority, weight, current_weight, pause_reason, daily_budget_usd_micros, daily_budget_tokens, batch_id}`; `work_locks.{owner_instance, heartbeat_at, lease_expires_at}`; `jobs.{waiting_reason, waiting_until, batch_id, pinned_config, attempt, cancel_requested_at}`; `provider_limits.{cooldown_until, consecutive_failures, last_error_code, last_error_at}`.
- Khóa settings: `scheduler.*`, `budget.*`, `autowrite.*` như bảng trên.
- API: `PUT /v1/queues/priority`, `GET/PUT /v1/settings/concurrency`, body `when` của pause.
- Mã: `AUTOWRITE_ACTIVE`, `CHAPTER_IS_BASE` (chung F11); lý do chờ `WORKER_POOL_FULL`, `PROVIDER_CONCURRENCY_FULL`, `WORK_PAUSED`; `pause_reason` `STALE`, `INTERRUPTED`, `PROVIDER_AUTH`.
- Event: `stream.tail`.
- Module: `modules/autowrite/`, `jobs/budget.py`.
