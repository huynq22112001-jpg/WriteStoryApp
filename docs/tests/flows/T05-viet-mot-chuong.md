# T05 — Viết một chương

Tính năng: F10. Nguồn: Plan FL04, §6.2, §6.4, §6.5, §4.2–4.3, §5 (`chapter_handoffs`, `chapter_plans`, `chapter_candidates`, `story_states`), §23.1.A–C. Cấp test chính: contract, integration.

## Mục đích

Chứng minh pipeline một chương (load → plan → compose → write → check → settle → validate → seam → review → commit) cho kết quả liền mạch: Writer nhận handoff + đuôi chương trước, chương chỉ được commit cùng state hợp lệ trong một transaction, và cổng vào chặn đúng khi chương trước chưa sẵn sàng.

## Tiền điều kiện và dữ liệu

- Data-root tạm; truyện `tests/fixtures/stories/tien_hiep_01/` (tiên hiệp, 3 chương đã commit, `story_states` 0–3, `chapter_handoffs` ch.3, hook #7 `due_by_chapter=4`, sự kiện E5 `planned_chapter=4`); continuity `ok`.
- Cấu hình: độ dài 2.500–3.500 âm tiết, K = 2 vòng sửa, vai trò theo T03-12.
- Mock provider (mặc định cho file này):
  `{latency_ms: 50, tokens_per_sec: 150, scripted_outputs: {plan: "tien_hiep_01/plan_ch04.json", write: "tien_hiep_01/ch04.txt", settle: "tien_hiep_01/delta_ch04.json", validate: {consistent: true}, seam: {pass: true}, review: "tien_hiep_01/review_ch04_minor.json", summary: "tien_hiep_01/summary_ch04.txt", usage: {cache_read_tokens: 1200, cache_write_tokens: 3000}}}`.
- Mock ghi lại toàn bộ request theo bước để kiểm nội dung prompt.

## Kịch bản

| ID | Loại | Bước | Kết quả mong đợi | Cấp | Tự động hóa |
|---|---|---|---|---|---|
| T05-01 | thành công | 1. Đăng ký `GET /v1/events?works=<id>`. 2. `POST /v1/jobs` `{type: write, work_id, chapter_no: 4, mode: auto, idempotency_key}`. 3. Chờ xong. | Response trả `job_id`, trạng thái `queued` ngay. Event theo thứ tự: `job.queued` → `job.state` (`running`) → `job.step` cho `load`, `plan`, `compose`, `write`, `check`, `settle`, `validate`, `seam`, `review`, `commit` → `token.delta` (gộp 50–100 ms) → `candidate.ready` → `finding.added` (minor) → `chapter.committed` (`chapter_no=4`) → `usage.updated` → `job.state` (`succeeded`). `seq` tăng nghiêm ngặt. | integration | `be/tests/integration/test_write_chapter_success.py` |
| T05-02 | thành công | Sau T05-01, đọc DB. | Một transaction đã ghi: `chapter_revisions` mới cho ch.4, con trỏ revision hiện tại của chương; `story_states` `chapter_no=4`; `chapter_handoffs` ch.4; `summaries` cấp chương ch.4; hook #7 `advance`/`resolve`; `timeline` ch.4; sự kiện E5 `done`; FTS chứa văn bản ch.4; `jobs` `succeeded`; `chapter_candidates` `accepted`; chương ch.4 có `state_applied=true`. | integration | như trên |
| T05-03 | thành công | Đọc request mock của bước `write` và `plan`. | Prompt Writer chứa `ending_state` ch.3 và `tail_text` ch.3 nguyên văn; prompt Planner chứa `tail_text` ch.3, KHÔNG chứa đoạn đầu ch.3 nằm ngoài `tail_text` (khác InkOS đưa toàn văn). Plan chứa sự kiện E5, hook #7 và yêu cầu cảnh mở nối `ending_state` ch.3. | contract | `ai/tests/contract/test_writer_receives_handoff.py` |
| T05-04 | thành công | Kiểm `chapter_handoffs` ch.4. | `tail_text` 1.000–2.000 token (ước lượng theo tokenizer của model), bắt đầu và kết thúc đúng ranh giới đoạn (`paragraph_id` đầu/cuối khớp đoạn nguyên); `ending_state` có địa điểm, thời điểm truyện, nhân vật có mặt + trạng thái, hành động dở dang, cảm xúc chủ đạo; có `open_threads`, `next_opening_requirements` và revision nguồn. | unit, integration | `ai/tests/unit/test_handoff_builder.py` |
| T05-05 | biên | Dùng model `max_input_tokens=16000`, summaries và kết quả FTS cố ý dài 30.000 token. | Composer nén/bỏ lớp compressible (summaries, FTS) cho vừa ngân sách; `plan`, `handoff`, `tail_text` có mặt nguyên văn; trace ghi phần bị nén. Nếu riêng phần bảo vệ đã vượt ngân sách: không gửi request, job `waiting_user` với lý do ngân sách context (không throw như InkOS). | contract | `ai/tests/contract/test_composer_protected_layers.py` |
| T05-06 | thành công | `POST /v1/jobs` write ch.4 không kèm `mode: auto` (viết từ AI panel); sau pipeline, `POST /v1/candidates/{id}/accept`. | Sau pipeline: job `waiting_user`, candidate `ready` kèm tóm tắt kiểm tra; chưa có revision ch.4. Sau accept: commit transaction như T05-02, job `succeeded`, event `chapter.committed`. | integration, e2e-fe | `be/tests/integration/test_write_chapter_manual_accept.py`, `fe/tests/e2e/ai_panel_write.spec.ts` |
| T05-07 | lỗi | Tiêm `WS_TEST_FAULT=commit:fts_insert` để lỗi giữa transaction commit. | Rollback toàn bộ: 0 dòng mới trong `chapter_revisions`, `story_states`, `chapter_handoffs`, `summaries`, `timeline` cho ch.4; hook/sự kiện không đổi; continuity vẫn `ok`; candidate giữ `ready`; job `failed` có `retryable=true`. Resume → commit thành công đúng 1 lần. | integration | `be/tests/integration/test_commit_atomicity.py` |
| T05-08 | lỗi | (a) Fixture ch.3 `state_applied=false`. (b) Continuity `blocked_needs_resync`. (c) Continuity `stale_from(2)`. Tạo job write ch.4. | Cả ba bị từ chối `WORK_BLOCKED`, `action` chỉ tới resync/xử lý chặn; 0 request tới provider; không tạo `chapter_plans`. | integration | `be/tests/integration/test_write_entry_gate.py` |
| T05-09 | lỗi | Tạo job write ch.3 (đã có) và ch.6 (bỏ qua ch.4–5). | Cả hai trả `CHAPTER_RANGE_CONFLICT` kèm chương kế tiếp đúng (4) trong `detail`. | integration | `be/tests/integration/test_write_chapter_number.py` |
| T05-10 | biên | Gửi 2 lần `POST /v1/jobs` cùng `idempotency_key`. | Cùng `job_id`; 1 dòng `jobs`; mock nhận đúng 1 chuỗi request. | integration | `be/tests/integration/test_job_idempotency.py` |
| T05-11 | biên | Khi job write ch.4 đang `running`, tạo job revise ch.3 cùng truyện. | Job thứ hai vào hàng đợi `waiting_slot` lý do khóa truyện, response kèm mã thông báo `WORK_BUSY_QUEUED` (không fail-fast 409 như InkOS); tại mọi thời điểm tối đa 1 job ghi `running` cho truyện; job thứ hai chạy sau khi job đầu xong và khóa được nhả. | integration | `be/tests/integration/test_work_lock_queue.py` |
| T05-12 | phục hồi | 1. Tiêm kill sau bước `plan`. 2. Khởi động lại, resume. 3. Lặp lại nhưng trước resume sửa handoff ch.3 qua `PUT /v1/chapters/{id}/handoff`. | Lần 2: dùng lại `chapter_plans` vì `input_hash` khớp, mock nhận 0 request `plan`. Lần 3: `input_hash` khác, tạo plan mới (1 request `plan`), plan cũ không dùng. | integration | `be/tests/integration/test_plan_input_hash.py` |
| T05-13 | biên | Mock `write` trả 1.800 âm tiết (dưới 2.500). | Bước `check` ghi số âm tiết và số ký tự vào measurement; tạo finding nguồn `check` về độ dài, kèm khoảng mục tiêu; xử lý theo mức độ đã chốt (đề xuất: kích hoạt sửa cục bộ, không cắt văn bản). | unit, integration | `ai/tests/unit/test_length_check.py` |
| T05-14 | biên | Mock `settle` không có thao tác nào cho hook #7 (`due_by_chapter=4`). | Sau chương 4, hook #7 quá hạn được báo: finding mở tham chiếu hook #7 và hiện ⚠ trong Story Bible/tab Nối; chương 5 plan đưa hook #7 vào mục bắt buộc. | integration | `be/tests/integration/test_hook_overdue_reported.py` |
| T05-15 | hủy | `POST /v1/jobs/{id}/cancel` khi đang stream bước `write` (sau ~500 token). | Request HTTP tới mock bị đóng (mock ghi nhận disconnect); job `cancelled`; candidate `partial` hiển thị được nhưng không phải chương hoàn chỉnh; 0 revision ch.4; khóa truyện nhả; job kế tiếp trong hàng đợi bắt đầu. | integration | `be/tests/integration/test_write_cancel.py` |
| T05-16 | hủy | Tiêm điểm dừng ngay trước transaction commit; gửi cancel; thả điểm dừng. Lặp lại với cancel gửi sau khi commit xong. | Cancel ghi nhận trước commit → không commit, job `cancelled`. Cancel sau commit → chương giữ nguyên committed, job `succeeded`, response cancel nêu job đã xong (hoàn tác bằng revision/restore). Không có trạng thái lai. | integration | `be/tests/integration/test_cancel_commit_race.py` |
| T05-17 | thành công | Đọc `usage_counters` và `job_steps` sau T05-01; lặp lại với mock không trả usage. | Usage cộng đúng số mock trả (gồm `cache_read_tokens`, `cache_write_tokens`); khi mock không trả usage, giá trị để trống/không xác định, không suy diễn. | integration | `be/tests/integration/test_usage_recording.py` |
| T05-18 | thành công | `GET /v1/chapters/{id}/trace` cho ch.4. | Liệt kê ngữ cảnh đã dùng (handoff ch.3, `tail_text`, summaries, hooks đến hạn, kết quả FTS kèm chương nguồn), prompt version mỗi bước, model + effort, usage. | integration | `be/tests/integration/test_chapter_trace.py` |
| T05-19 | biên | Viết ch.4 rồi ch.5; so request bước `write`. | Lớp 1–2 của prompt giống hệt từng byte giữa hai chương (hash bằng nhau) để tận dụng prompt cache; lớp 3–4 khác. | contract | `ai/tests/contract/test_prompt_layer_prefix.py` |
| T05-20 | hiệu năng | 100 lần `POST /v1/jobs` (mock chậm, không chờ xong). | p95 thời gian trả response < 300 ms trên máy tham chiếu. | integration | `be/tests/integration/test_job_create_latency.py` |

## Kiểm tra dữ liệu sau test

- DB: như T05-02; mỗi chương committed có `state_applied=true`, đúng 1 `story_states` và 1 `chapter_handoffs` cùng `chapter_no`; `chapter_plans` có `input_hash`.
- `job_steps`: đủ các bước, mỗi bước có prompt version, model, effort, timing, usage, checkpoint.
- Event: thứ tự như T05-01; event (trừ `token.delta`) có trong `job_events` để replay.
- File: không có file tạm sót trong `data/tmp/` sau commit/rollback.

## Tiêu chí pass

- 0 chương committed có `state_applied=false` trong toàn bộ file test.
- 100% request bước `write` chứa `tail_text` và `ending_state` của chương trước.
- Lỗi giữa commit để lại 0 dòng dở dang (kiểm bằng đếm dòng trước/sau).
- Cancel trước commit ngăn commit 100% trong 50 lần lặp T05-16 có jitter thời điểm.
- p95 tạo job < 300 ms (tiêu chí đề xuất §4.4).

## Ghi chú thủ công

- Live (`live`, chỉ khi có key): viết ch.4 của truyện mẫu bằng model thật, tác giả đọc đoạn mở ch.4 so với đuôi ch.3 và chấm mối nối (khớp địa điểm, thời điểm, nhân vật, cảm xúc).

## Tên mới đề xuất

- Tên bước (`job.step` payload và mock): `load`, `plan`, `compose`, `write`, `check`, `settle`, `validate`, `seam`, `review`, `repair`, `commit`, `summary`.
- `chapters.state_applied` (chỉ số §9 dùng nhưng §5 chưa có cột) và `chapters.status` (Review §4.4: `drafting`/`checking`/`revising`/`committed`/`waiting_user`).
- Trường `mode` trong `POST /v1/jobs` cho job write đơn lẻ (`auto` = tự commit khi qua cổng; không có = dừng `waiting_user` chờ accept).
- `jobs.wait_reason` (lý do `waiting_slot`: `worker`, `provider`, `work_lock`, `budget`, `VAULT_LOCKED`, `PROVIDER_UNREACHABLE`, `PROVIDER_RATE_LIMIT`).
- Mã lý do ngân sách context: `CONTEXT_BUDGET_EXCEEDED`.
- Loại finding `hook` (hook quá hạn) và `length` (độ dài ngoài khoảng).
- Tham số mock `scripted_outputs.usage`.
