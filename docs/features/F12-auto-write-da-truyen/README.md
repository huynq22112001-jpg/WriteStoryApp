# F12 — Auto-write đa truyện

Giai đoạn: R2. Trạng thái: planned.

## Mục tiêu

Tác giả bật auto-write cho nhiều truyện cùng lúc; app chạy song song giữa các truyện, tuần tự tuyệt đối trong một truyện, chia slot công bằng, tôn trọng giới hạn provider và ngân sách, luôn nói rõ vì sao một truyện đang chờ. Phòng viết cho thấy mọi truyện đang ở bước nào và cho tạm dừng/tiếp tục/đổi ưu tiên; app khởi động lại thì tiếp tục được từ checkpoint.

## Phạm vi

- Trong phạm vi:
  - Global scheduler một process: ready set, xoay vòng công bằng có trọng số, mỗi truyện tối đa 1 job ghi, worker pool mặc định 4 (Plan §4.2, Review §5.1).
  - `work_queues`, `work_locks` (lease + heartbeat), trạng thái `waiting_slot` có lý do (Plan §4.2, §4.3).
  - Provider limiter: concurrency, token bucket RPM/TPM, `Retry-After`, backoff + jitter, không retry 401/403/model-not-found (Plan §4.2, Review §5.2).
  - Ngân sách token/chi phí theo ngày, theo truyện và toàn app, theo timezone cấu hình (Plan §4.2, §14.2).
  - Lý do chờ: worker đầy, provider đầy, rate limit, hết ngân sách, khóa truyện, vault khóa, provider không phản hồi (Plan §23.2 #7 #8).
  - Ba chế độ `auto`, `review_each`, `review_every_k`; API autowrite + pause/resume/cancel + estimate (Plan §4.2, §7, §23.2 #6; FL05).
  - State machine job (Plan §4.3); quy tắc sửa tay khi đang chạy (Plan §23.2 #3); reconcile/resume sau restart (Plan §4.3, FL01 bước 3).
  - FE: Phòng viết (UI §5.3), hộp thoại auto-write có ước tính (Plan §23.4 #5), chỉ báo header "N truyện đang chạy" (UI §4).
- Ngoài phạm vi:
  - Pipeline một chương (F10); candidate/resync (F11) – F12 chỉ lập lịch các job đó.
  - Scheduler theo lịch cron, tray/background khi đóng cửa sổ (FL24 phần lịch, `jobs/cron.py`, R7).
  - Ghi nhận usage/chi phí và thông báo native, giữ máy thức (F14) – F12 đọc bộ đếm của F14 để kiểm ngân sách.
  - Model dự phòng khi lỗi kéo dài (Plan §23.3 #10, Sau MVP).

## Phụ thuộc

| Cần có trước | Lý do |
|---|---|
| F01 | Event `job.*`, `queue.changed`, `provider.status`; mã lỗi `WORK_BUSY_QUEUED`, `BUDGET_EXCEEDED`… |
| F02 | Bảng `jobs`/`job_steps`/`job_events`, writer queue, supervisor bền vững |
| F03 | Trạng thái vault (`VAULT_LOCKED`) và sự kiện mở vault |
| F04 | `providers`, `provider_models` (giá, đồng thời riêng), `role_models`, model resolver ghim cấu hình |
| F10 | Job `write` (pipeline §6.2) có checkpoint theo bước |
| F11 | `continuity_status`, job `revise`/`resync` |
| F14 | `usage_counters` (đọc để kiểm ngân sách), keep-awake, thông báo |

## Nguồn thiết kế

- Plan §2 (asyncio), §4.2, §4.3, §4.4 (3–5 truyện song song), §5 (`work_queues`/`work_locks`, `provider_limits`/`usage_counters`), §7 (autowrite, queues), §7.1 (ghim model + effort), §9 Giai đoạn 3, §14.2 (quota InkOS dùng UTC), §21 dòng "Đa truyện" và "Scheduler, FL24", §23.1.C, §23.2 #3 #6 #7 #8.
- FL05, FL24 (phần quota), FL26 bước 4.
- Arch §5 (`jobs/scheduler.py`, `jobs/locks.py`, `infrastructure/ai/limits.py`, `model_resolver.py`), §6 (retry transport do AI policy sở hữu).
- UI §4 (header, status bar), §5.3, §5.6.3, §6, §8 (Ctrl+Shift+W).
- Review §2.2, §5.
- Mã Plan §15: LNG08, OPS01, OPS02 (một phần), MOD09.

## Phân rã

| Tầng | File | Tóm tắt |
|---|---|---|
| BE | [be.md](./be.md) | Scheduler, khóa, limiter, ngân sách, state machine job, API autowrite/queues/estimate, reconcile |
| FE | [fe.md](./fe.md) | Phòng viết, hộp thoại auto-write, header/status bar, kéo thả ưu tiên, log và biểu đồ chi phí |
| AI | [ai.md](./ai.md) | Cách job gọi pipeline với cấu hình đã ghim; ranh giới limiter (BE) và retry transport (AI policy) |

## Tiêu chí hoàn thành

- [ ] 5 truyện mock (độ trễ thật) chạy đồng thời với pool 4: mọi truyện đều tiến, không truyện nào chờ quá một vòng xoay khi đủ điều kiện (Plan §9 Giai đoạn 3).
- [ ] Trong một truyện không bao giờ có 2 job ghi `running`; chương N+1 chỉ tạo sau khi N commit.
- [ ] 429 giả lập được chờ đúng `Retry-After`; 401 không retry, batch dừng với lý do rõ.
- [ ] Hết ngân sách → job `waiting_slot` lý do `BUDGET_EXCEEDED`, tự chạy lại khi qua ngày theo timezone cấu hình.
- [ ] Vault khóa → `waiting_slot` `VAULT_LOCKED`; mở vault thì chạy tiếp không tạo lại job.
- [ ] Kill process giữa bước → khởi động lại thấy `interrupted`, resume từ checkpoint hợp lệ cuối; cancel trước commit ngăn commit.
- [ ] Không có lỗi `database is locked` khi 5 truyện commit gần nhau; editor vẫn gõ mượt (đo thủ công ở R2).
- [ ] Phòng viết hiển thị bước pipeline, vòng sửa `↻ k/K`, lý do chờ với đếm ngược, 2 dòng cuối cập nhật ~4 lần/giây.
- [ ] Các test luồng liên quan pass: [T07](../../tests/flows/T07-auto-write-mot-truyen.md), [T08](../../tests/flows/T08-da-truyen-dong-thoi.md), [T09](../../tests/flows/T09-huy-crash-va-phuc-hoi.md), [T15](../../tests/flows/T15-loi-provider.md), [T17](../../tests/flows/T17-phong-viet-va-su-kien.md).

## Rủi ro và câu hỏi mở

- Một job dùng nhiều vai trò có thể thuộc nhiều provider; MVP xét slot provider theo provider của bước kế tiếp (giả định), chờ RPM/TPM trong lúc job đang giữ worker.
- Giá trị lease 60 giây, heartbeat 20 giây, trọng số ưu tiên truyện đang mở là giả định, chỉnh sau đo.
- Ước tính chi phí khi truyện chưa có chương nào dựa trên tỷ lệ token/âm tiết giả định; hiển thị rõ "ước tính thô".
- FL05 ghim cấu hình theo batch, còn §7.1/UI §5.6.2 ghim theo job và áp từ chương kế tiếp; F12 chọn ghim theo job chương (xem báo cáo mâu thuẫn).
- Máy ngủ: không hứa xử lý khi sleep (FL24); chỉ giữ máy thức qua F14.
