# T09 — Hủy, crash và phục hồi

Tính năng: F02, F12. Nguồn: Plan §4.3, §6.6 (timeout, cancel), §5 (WAL, `synchronous=FULL`), §9 Giai đoạn 3, §11 (Job recovery), §21, §23.2 #9, Arch §8 bước 8. Cấp test chính: integration.

## Mục đích

Chứng minh hủy luôn được truyền tới request HTTP và ngăn commit, kill tiến trình ở bất kỳ bước nào cũng không để lại dữ liệu nửa vời, job đang chạy được reconcile thành `interrupted` và resume từ bước hợp lệ cuối cùng mà không làm state truyện đi trước bản thảo.

## Tiền điều kiện và dữ liệu

- Backend chạy như tiến trình con của test (`python -m writestory_be` với data-root tạm) để kill thật (`SIGKILL`/`TerminateProcess`).
- Truyện `tests/fixtures/stories/tien_hiep_01/` (3 chương committed).
- Điểm tiêm lỗi `WS_TEST_FAULT=kill:after_step:<step>` và `kill:during_step:<step>:<token_count>` với `<step>` thuộc `plan`, `compose`, `write`, `check`, `settle`, `validate`, `seam`, `review`, `repair`, `commit`.
- Mock provider: `{latency_ms: 50, tokens_per_sec: 100, scripted_outputs: <như T05>}`; mock lưu số request theo bước để đếm chi phí phát sinh khi retry.

## Kịch bản

| ID | Loại | Bước | Kết quả mong đợi | Cấp | Tự động hóa |
|---|---|---|---|---|---|
| T09-01 | hủy | Cancel job `queued` (chưa chạy). | Job `cancelled` ngay; 0 request tới mock; không tạo `chapter_plans`/candidate. | integration | `be/tests/integration/test_cancel_queued.py` |
| T09-02 | hủy | Cancel job `waiting_slot` (đang chờ provider). | Job `cancelled`; slot không bị giữ; job khác nhận slot. | integration | `be/tests/integration/test_cancel_waiting_slot.py` |
| T09-03 | hủy | Cancel khi đang stream `write`. | Kết nối HTTP tới mock đóng trong ≤ 1 s; mock không còn sinh token; job `cancelled`; candidate `partial` lưu bản nháp; 0 revision; khóa truyện nhả. | integration | `be/tests/integration/test_cancel_propagates_http.py` |
| T09-04 | hủy | Cancel job đang `waiting_user` (candidate `ready`). | Job `cancelled`; candidate chuyển `rejected`; continuity của truyện không đổi nếu chưa bị chặn; nếu đang `blocked_needs_resync` thì vẫn giữ (hủy job không gỡ chặn). | integration | `be/tests/integration/test_cancel_waiting_user.py` |
| T09-05 | phục hồi | Lặp qua từng `<step>`: kill sau bước đó; khởi động lại; `POST /v1/jobs/{id}/resume`. | Sau restart job `interrupted`, `job_steps` có checkpoint của bước cuối hoàn tất; resume chạy tiếp từ bước kế tiếp (mock nhận 0 request cho các bước đã hoàn tất có checkpoint hợp lệ); kết quả cuối giống chạy liền mạch (so state ch.4 và văn bản). | integration | `be/tests/integration/test_kill_each_step_resume.py` |
| T09-06 | phục hồi | Kill giữa stream `write` sau 800 token; khởi động lại. | Candidate `partial` hiển thị trong UI với nhãn "bản nháp chưa hoàn chỉnh", không phải chương; resume chạy lại bước `write` (không hứa nối tiếp từng token); usage ghi nhận cả lần bị kill nếu provider đã trả usage, không suy diễn khi không có. | integration | `be/tests/integration/test_kill_mid_stream.py` |
| T09-07 | phục hồi | Kill trong transaction commit (`kill:during_step:commit`), lặp 30 lần với thời điểm ngẫu nhiên. | Sau restart: hoặc đủ mọi dòng của commit (revision, state, handoff, summary, hooks, timeline, FTS, job result), hoặc không dòng nào; `PRAGMA integrity_check` = `ok`; nếu commit chưa xảy ra, resume commit đúng 1 lần. | integration | `be/tests/integration/test_kill_during_commit.py` |
| T09-08 | phục hồi | Kill khi 3 truyện đang auto-write ở các bước khác nhau. | Sau restart cả 3 job `interrupted`; khóa `work_locks` được thu hồi; resume từng truyện độc lập; mỗi truyện tiếp đúng chương đang dở, không lặp/nhảy số chương. | integration | `be/tests/integration/test_kill_multi_work.py` |
| T09-09 | phục hồi | Interrupted job ch.4; trước khi resume, tác giả sửa tay ch.2 → `stale_from(2)`. | Resume bị từ chối `WORK_BLOCKED` (`action` = resync); job giữ `interrupted`; sau resync xong mới resume được. | integration | `be/tests/integration/test_resume_blocked_by_stale.py` |
| T09-10 | phục hồi | Interrupted job; trước resume đổi model vai trò Viết. | Resume dùng model + effort đã ghim trong job (không đổi ngầm); trace ghi model ghim. | integration | `be/tests/integration/test_resume_pinned_config.py` |
| T09-11 | phục hồi | Kill ở bước `repair` vòng 2. | Resume tiếp vòng 2 (không reset bộ đếm vòng về 0); tổng vòng sửa của chương ≤ K. | integration | `be/tests/integration/test_resume_repair_round.py` |
| T09-12 | lỗi | Resume job đã `succeeded`/`cancelled`. | Trả `VALIDATION` với trạng thái hiện tại; không tạo request mới. | integration | `be/tests/integration/test_resume_invalid_state.py` |
| T09-13 | phục hồi | Mô phỏng máy ngủ: mock treo kết nối không trả byte trong thời gian > stream-idle timeout. | Hết timeout stream-idle → bước lỗi tạm thời, chạy lại từ checkpoint (không fail cả job ngay); timeout first-token và overall deadline được áp riêng (cấu hình test 2 s/5 s/30 s). | integration | `be/tests/integration/test_timeouts_and_sleep.py` |
| T09-14 | phục hồi | Kill backend khi FE đang mở Phòng viết. | FE hiện "backend dừng bất ngờ – khởi động lại"; bấm khởi động lại → shell spawn backend mới, FE reconnect từ `seq` cuối, các job hiện `interrupted` kèm nút Resume (chi tiết event ở T17). | e2e-fe, desktop | `fe/tests/e2e/backend_crash_banner.spec.ts` |
| T09-15 | biên | Đếm request mock trong T09-05 cho bước bị kill giữa chừng. | Số request tăng thêm đúng bằng các bước phải chạy lại; báo cáo ghi chi phí phát sinh do retry (không hứa exactly-once billing). | integration | như T09-05 |
| T09-16 | phục hồi | Mất điện mô phỏng: kill ngay sau khi API báo commit thành công. | Sau restart chương vẫn committed (FULL fsync); file `-wal`/`-shm` không bị xóa thủ công; integrity `ok`. | integration | `be/tests/integration/test_durability_after_commit.py` |

## Kiểm tra dữ liệu sau test

- DB: không có job `running` sau restart; mọi job bị kill ở `interrupted` với checkpoint; không có `story_states` hay `chapter_handoffs` của chương chưa có revision committed; `work_locks` sạch.
- `job_steps`: checkpoint của bước cuối hoàn tất; bộ đếm vòng sửa giữ nguyên qua restart.
- Event: `job.state` `interrupted` phát khi reconcile; `job.state` `running` khi resume.
- File: `data/tmp/` không còn file tạm của commit bị kill sau lần khởi động kế tiếp (dọn mồ côi).

## Tiêu chí pass

- 0 lần state truyện đi trước bản thảo (mọi `story_states` chương N đều có revision committed chương N) qua toàn bộ ma trận kill × bước.
- 30/30 lần kill trong commit cho kết quả "đủ hoặc không" và `integrity_check` = `ok`.
- Cancel trước commit ngăn commit 100%; kết nối HTTP đóng ≤ 1 s sau cancel.
- Resume không gọi lại bước đã có checkpoint hợp lệ (0 request thừa cho các bước đó).

## Ghi chú thủ công

- Trên máy thật: bật "giữ máy thức khi đang viết", cho máy ngủ bằng tay khi tắt tùy chọn này, đánh thức và xác nhận job chạy lại từ checkpoint (Windows `SetThreadExecutionState`, macOS IOPMAssertion).

## Tên mới đề xuất

- Điểm tiêm lỗi `kill:after_step:<step>`, `kill:during_step:<step>:<token_count>` (dùng chung `WS_TEST_FAULT`).
- Cấu hình timeout: `connect_timeout`, `first_token_timeout`, `stream_idle_timeout`, `overall_deadline` (Plan §6.6 nêu bốn loại nhưng chưa đặt tên khóa).
