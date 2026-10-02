# T08 — Đa truyện đồng thời

Tính năng: F12. Nguồn: Plan §4.2 (scheduler, khóa, limiter, ngân sách, writer queue), §4.3, §4.4, FL05, FL24 bước 2–3, §9 Giai đoạn 3–4, §21 (dòng "Đa truyện"), Review §2.2, §2.3 #6–7, §5. Cấp test chính: integration.

## Mục đích

Chứng minh nhiều truyện chạy song song mà không truyện nào bị bỏ đói (khác lỗi `activeBooks.slice(0, N)` của InkOS), mỗi truyện vẫn tuần tự, limiter theo provider tôn trọng concurrency/RPM/TPM/`Retry-After`, hết ngân sách chỉ chặn đúng phạm vi, một truyện bị chặn không ảnh hưởng truyện khác, và SQLite không báo `database is locked`.

## Tiền điều kiện và dữ liệu

- 6 truyện từ `tests/fixtures/stories/` (`tien_hiep_01`, `do_thi_01` và 4 bản sao đổi tên A–F), mỗi truyện 3 chương committed, thứ tự tạo A → F.
- Worker pool = 2 (T08-01..03), = 4 (các kịch bản khác); provider P1 cloud `max_concurrent_requests=3`, RPM 60; provider P2 local `max_concurrent_requests=1`.
- Mock provider: `{latency_ms: 300, tokens_per_sec: 100, scripted_outputs: <bộ 20 chương như T07>}`; kịch bản rate limit: `fail_sequence: [429(retry_after=2), ok]`; kịch bản lỗi chung: `fail_sequence: [500, 500, ok]`.
- Đồng hồ giả `WS_TEST_CLOCK`, timezone `Asia/Ho_Chi_Minh`; trace scheduler bật (ghi mỗi lần cấp slot: thời điểm, work_id, job_id).

## Kịch bản

| ID | Loại | Bước | Kết quả mong đợi | Cấp | Tự động hóa |
|---|---|---|---|---|---|
| T08-01 | thành công | Worker pool 2; 6 truyện cùng `autowrite {count: 5, mode: auto}`, cùng ưu tiên. | Mọi truyện A–F được cấp slot lần đầu trong 3 vòng cấp slot đầu tiên (⌈6/2⌉); khoảng cách giữa hai lần cấp slot của một truyện ready ≤ 3 vòng; cả 6 truyện đều có chương commit. Đối chứng: một bộ lập lịch giả lập kiểu `slice(0, 2)` trên cùng trace cho truyện C–F 0 chương (test chứng minh test bắt được lỗi bỏ đói). | integration | `be/tests/integration/test_scheduler_fairness.py` |
| T08-02 | biên | Như T08-01, truyện E là truyện người dùng đang mở (cộng trọng số ưu tiên). | E được cấp slot nhiều hơn mỗi truyện khác nhưng mọi truyện vẫn tiến: không truyện ready nào chờ quá 2× chu kỳ xoay vòng không có ưu tiên. | integration | `be/tests/integration/test_scheduler_priority_weight.py` |
| T08-03 | biên | Kéo D lên đầu hàng đợi ưu tiên trong Phòng viết. | API cập nhật ưu tiên, event `queue.changed`; slot kế tiếp trống cấp cho D; thứ tự lưu bền sau restart. | integration, e2e-fe | `be/tests/integration/test_queue_priority_change.py`, `fe/tests/e2e/writing_room_priority.spec.ts` |
| T08-04 | thành công | 5 truyện auto-write với worker pool 4, provider P1 limit 3. | Số request đồng thời tới P1 không vượt 3 tại mọi thời điểm (mock đếm); số job `running` ≤ min(4, 3); job còn lại `waiting_slot` lý do provider đầy; status bar hiện "3/3 slot". | integration | `be/tests/integration/test_provider_concurrency_limit.py` |
| T08-05 | thành công | 3 truyện dùng P1, 2 truyện dùng P2 (local). | Giới hạn tính riêng theo provider: P2 tối đa 1 request đồng thời, P1 tối đa 3; truyện dùng P2 không chiếm slot P1 (một semaphore toàn app không thay giới hạn từng provider). | integration | `be/tests/integration/test_limiter_per_provider.py` |
| T08-06 | lỗi | `fail_sequence: [429(retry_after=2), ok]` cho request đầu tiên của truyện A. | Không request nào tới P1 trong 2 s sau khi nhận 429 (đo theo mock); job A `waiting_slot` lý do `PROVIDER_RATE_LIMIT` trong thời gian chờ; event `provider.status`; sau đó A chạy tiếp, không tính là thất bại. | integration | `be/tests/integration/test_retry_after.py` |
| T08-07 | lỗi | 429 không có header `Retry-After`, lặp 4 lần. | Retry tối đa 3 lần với exponential backoff + jitter (khoảng cách tăng dần, không cố định); sau lần thứ 3 xử lý theo chính sách lỗi kéo dài (`waiting_slot` lý do `PROVIDER_RATE_LIMIT`, không vòng retry vô hạn trong cùng request). | unit, integration | `ai/tests/unit/test_retry_policy.py` |
| T08-08 | lỗi | RPM P1 = 6; 5 truyện cùng chạy. | Số request trong mọi cửa sổ 60 s ≤ 6 (token bucket); TPM tính theo usage thực; không có 429 do vượt RPM tự gây. | integration | `be/tests/integration/test_token_bucket.py` |
| T08-09 | lỗi | Ngân sách truyện B = $0,10/ngày, toàn app $10; 4 truyện chạy. | Khi B chạm ngân sách: job kế tiếp của B `waiting_slot` lý do `BUDGET_EXCEEDED`; A, C, D tiếp tục; Phòng viết hiện "hết ngân sách truyện" cho B. Qua 00:00 theo timezone cấu hình, B tự chạy tiếp. | integration | `be/tests/integration/test_budget_per_work.py` |
| T08-10 | lỗi | Ngân sách toàn app hết giữa chừng; khởi động lại backend trước 00:00. | Mọi job viết `waiting_slot` lý do `BUDGET_EXCEEDED`; sau restart bộ đếm `usage_counters` giữ nguyên (không reset về 0 như quota trong RAM của InkOS); qua ngày mới tự chạy. | integration | `be/tests/integration/test_budget_global_persist.py` |
| T08-11 | lỗi | Truyện C rơi vào `blocked_needs_resync` (seam fail mãi, như T06-02) khi A, B, D đang chạy. | C dừng ở `waiting_user`; scheduler không cấp slot viết mới cho C; slot của C được cấp cho truyện khác trong ≤ 1 vòng; số chương commit của A, B, D không giảm so với lần chạy đối chứng. | integration | `be/tests/integration/test_blocked_work_no_impact.py` |
| T08-12 | biên | Mock cho 5 truyện kết thúc bước `review` cùng một thời điểm (đồng bộ bằng barrier) để commit gần như đồng thời; lặp 50 lần. | 0 lỗi `database is locked`; mọi commit đi qua writer queue; mỗi commit thành công đúng 1 lần; `busy_timeout` không bị chạm (ghi số đo thời gian chờ writer queue). | integration | `be/tests/integration/test_writer_queue_concurrent_commits.py` |
| T08-13 | phục hồi | Truyện A giữ khóa; tiêm treo heartbeat (`WS_TEST_FAULT=lock:heartbeat_stop`) quá lease. | Sau khi lease hết, khóa được thu hồi; job A chuyển `interrupted`; job kế tiếp của A có thể lấy khóa; không có hai job ghi của A cùng `running`. | integration | `be/tests/integration/test_work_lock_lease.py` |
| T08-14 | biên | Đổi worker pool từ 4 xuống 2 trong Settings khi 4 job đang chạy. | Không hủy job đang chạy; job mới chỉ được cấp khi số `running` < 2. | integration | `be/tests/integration/test_worker_pool_resize.py` |
| T08-15 | hiệu năng | 5 truyện auto-write với mock trễ thật (300 ms, 100 token/s) trong khi FE gõ liên tục vào editor truyện thứ 6. | Độ trễ gõ phím p95 < 50 ms (đề xuất, đo ở R0); event backend → UI p95 < 200 ms; Phòng viết cập nhật đuôi ~4 lần/giây; mọi truyện đều có chương commit. | e2e-fe | `fe/tests/e2e/multi_stream_typing_perf.spec.ts` |
| T08-16 | thành công | 3 truyện mẫu × 20 chương song song (`auto`), sau đó chạy bộ kiểm chỉ số liền mạch cho từng truyện. | Đạt mọi tiêu chí "Tiêu chí pass" bên dưới; báo cáo chỉ số lưu tại `tests/integration/reports/`. | integration | `tests/integration/test_continuity_metrics_parallel.py` |

## Kiểm tra dữ liệu sau test

- DB: mỗi truyện có chuỗi chương committed liên tục; `work_locks` không còn khóa của job đã kết thúc; `usage_counters` đúng theo truyện và toàn app, theo ngày và timezone; `provider_limits` không đổi sau test.
- Trace scheduler: danh sách cấp slot để tính độ công bằng (số lần cấp mỗi truyện, khoảng chờ tối đa).
- Event: `queue.changed` khi đổi ưu tiên/cấp slot; `provider.status` khi 429/limit; `job.state` với lý do `waiting_slot`.
- Log: 0 dòng `database is locked`.

## Tiêu chí pass

- Không bỏ đói: mọi truyện ready được cấp slot trong ≤ ⌈số truyện ready / số slot⌉ vòng; 6/6 truyện có chương commit ở T08-01.
- Concurrency thực tế không bao giờ vượt `min(worker pool, giới hạn provider)` và giới hạn riêng từng provider.
- 0 request gửi trước khi hết `Retry-After`; 0 retry với 401/403/model không tồn tại.
- 0 lỗi `database is locked` qua 50 lần T08-12.
- Truyện bị chặn/hết ngân sách: các truyện khác giữ ≥ 95% thông lượng so với đối chứng.
- T08-16, từng truyện: 0 chương committed có `state_applied=false`; seam pass ≥ 95% sau ≤ 2 vòng sửa; 0 tên ngoài canon chưa khai báo; 0 lỗi xưng hô không có `address.change`; 0 trộn kiểu bỏ dấu; 100% hook quá hạn được báo; n-gram trùng giữa chương liền kề dưới ngưỡng.

## Ghi chú thủ công

- Chạy T08-16 với provider thật (`live`) ở quy mô nhỏ (3 truyện × 5 chương) để quan sát 429 thật và hiệu quả prompt cache (`cache_read_tokens` tăng từ chương 2).

## Tên mới đề xuất

- `PUT /v1/queues/order` hoặc `PATCH /v1/works/{id}/autowrite` `{priority}` cho kéo thả ưu tiên (UI §5.3 nhắc "gọi API cập nhật priority" nhưng §7 chưa có).
- `PUT /v1/settings/concurrency` (worker pool, ngân sách, timezone) — §7 chưa có endpoint cài đặt ngoài `roles`.
- Trace scheduler `slot_grants` (chỉ bật trong test/debug).
- Điểm tiêm lỗi `lock:heartbeat_stop`.
