# F14 — Thông báo, nhật ký và chi phí

Giai đoạn: R2. Trạng thái: planned.

## Mục tiêu

Tác giả được báo khi chương bị chặn, batch xong hoặc provider lỗi kéo dài (cả thông báo hệ điều hành lẫn trung tâm thông báo trong app); biết đã tốn bao nhiêu token/tiền theo truyện, model, giờ và hiệu quả cache; xem nhật ký để tự chẩn đoán; máy không ngủ khi đang auto-write; xem và dọn dung lượng dữ liệu theo chính sách giữ rõ ràng.

## Phạm vi

- Trong phạm vi:
  - Thông báo native qua Tauri notification plugin + trung tâm thông báo, outbox bền (Plan §23.2 #12, §23.4 #9, FL24 bước 4).
  - Ghi nhận usage/chi phí mỗi request AI: token vào/ra, cache read/write, giá snapshot từ `provider_models`, bộ đếm theo ngày/timezone `usage_counters` (Plan §4.3, §5, §6.5, §7 `GET /v1/providers/{id}/usage`).
  - Trang Nhật ký `/logs`: chi phí (biểu đồ), yêu cầu AI, sự kiện job, log hệ thống (UI §4, §5.3 biểu đồ chi phí).
  - Log debug request/response AI tùy chọn trong `data/logs/ai/`, che secret, giới hạn dung lượng (Plan §23.2 #11).
  - Giữ máy thức khi đang auto-write: Rust `SetThreadExecutionState` (Windows) / IOPMAssertion (macOS) (Plan §23.2 #9).
  - Trang Lưu trữ: dung lượng theo loại, dọn dẹp theo chính sách giữ (Plan §23.2 #10, §23.4 #10).
- Ngoài phạm vi:
  - Telegram/Feishu/webhook (OPS09, R7); tray/background khi đóng cửa sổ (NEW07, R7).
  - Kiểm ngân sách và quyết định chờ (F12) – F14 chỉ cung cấp bộ đếm.
  - Analytics nâng cao (OPS05 phần R3–R4), Doctor (MOD10, F04).

## Phụ thuộc

| Cần có trước | Lý do |
|---|---|
| F00 | Rust shell: command giữ máy thức, notification plugin, capability; log Rust |
| F01 | Event envelope (`usage.updated`, `backend.notice`), hợp đồng lỗi |
| F02 | Writer queue; bảng `jobs`/`job_steps`/`job_events` |
| F04 | `provider_models` (giá/1M token gồm đọc/ghi cache), `providers` |
| F12 | Nguồn sự kiện chặn/xong batch/lỗi provider; số job đang chạy để giữ máy thức |
| F11, F13 | Candidate cần dọn; backup/export chiếm dung lượng |

## Nguồn thiết kế

- Plan §3.1 (`data/logs/` đã che secret), §4.3 (usage gồm cache read/write), §5 (`provider_limits / usage_counters`, `provider_models` giá), §6.4 (giá cache Anthropic), §6.6 cuối ("Lưu usage thực nhận; không suy diễn token"), §7, §18 (`notification_outbox`, `quota_counters`), §21 dòng "Scheduler, FL24" (notification failure sau commit), §23.2 #9–#12.
- FL24 bước 3–4; FL04 bước 9 (thông báo sau commit).
- Arch §5 `infrastructure/ai/progress_adapter.py`, §6 `contracts/usage.py`, §9 dòng OPS.
- UI §4 (ribbon Nhật ký, header "$ hôm nay"), §5.3, §5.8, §8.
- Review §6 (ghi `cache_read_tokens` để đo hiệu quả).
- Mã Plan §15: OPS05 (phần token usage, R2), OPS08, OPS10 (một phần).

## Phân rã

| Tầng | File | Tóm tắt |
|---|---|---|
| BE | [be.md](./be.md) | `notification_outbox`, `usage_records`, `usage_counters`, tính giá, API usage/logs/storage/notifications, log debug AI, dọn dẹp |
| FE | [fe.md](./fe.md) | Trung tâm thông báo + gửi native, trang Nhật ký + biểu đồ, trang Lưu trữ, hook giữ máy thức; Rust command `set_keep_awake` |
| AI | [ai.md](./ai.md) | Chỉ contract báo usage (`Usage`, chuẩn hóa theo giao thức) và `RequestTrace` cho log debug |

## Tiêu chí hoàn thành

- [ ] Mọi request AI có một dòng `usage_records`; token chỉ ghi khi provider trả (`reported=false` khi không có), không suy diễn.
- [ ] Chi phí tính bằng micro-USD từ giá snapshot lúc gọi; model thiếu giá → hiển thị "chưa có giá", vẫn đếm token.
- [ ] Bộ đếm ngày theo `budget.timezone`, khớp tổng `usage_records` cùng ngày (test đối soát).
- [ ] Chương bị chặn/batch xong/provider lỗi kéo dài tạo thông báo; lỗi gửi native không ảnh hưởng chương đã commit (FL24).
- [ ] Log debug AI tắt mặc định; bật thì không có API key/Authorization trong file (test quét pattern); tổng dung lượng không vượt giới hạn.
- [ ] Giữ máy thức bật khi có ≥ 1 truyện đang chạy và tùy chọn bật; nhả khi hết job hoặc app thoát.
- [ ] Trang Lưu trữ hiển thị dung lượng theo loại; dọn dẹp không bao giờ xóa revision đã commit.
- [ ] Các test luồng liên quan pass: [T15](../../tests/flows/T15-loi-provider.md), [T17](../../tests/flows/T17-phong-viet-va-su-kien.md), [T07](../../tests/flows/T07-auto-write-mot-truyen.md) (thông báo batch xong).

## Rủi ro và câu hỏi mở

- Chuẩn hóa usage giữa Anthropic và OpenAI-compatible (input có/không gồm cache) phải kiểm lại với tài liệu chính thức khi code; ghi trong ai.md là giả định.
- Giữ máy thức do FE gọi Rust khi nhận `queue.changed`; nếu webview bị hệ điều hành treo khi ẩn cửa sổ, cân nhắc BE báo Rust qua pipe bootstrap. Gập máy vẫn ngủ theo chính sách OS (không hứa, FL24).
- `dbstat` có thể không bật trong SQLite của Python đóng gói; khi không có, dung lượng từng bảng là ước lượng.
- Log debug AI chứa toàn văn bản thảo (dữ liệu cá nhân); cảnh báo rõ khi bật.
- Plan §5 gọi bộ đếm là `usage_counters`, §18 gọi `quota_counters`; F14 dùng `usage_counters` (xem báo cáo mâu thuẫn).
