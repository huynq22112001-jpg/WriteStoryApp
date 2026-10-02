# P011 – Rust: spawn backend + readiness

| Làn | Tính năng | Phụ thuộc |
|---|---|---|
| DESKTOP | F00 | [P010](./P010-rust-data-root-lock.md), [P003](./P003-kiem-chung-be-base.md) |

Dán nguyên khối dưới vào một cửa sổ Claude Code mới mở tại `E:\pm\WriteStoryApp`. Trạng thái của prompt được theo dõi trong [README.md](./README.md#tiến-độ).

```text
[P011] Rust: spawn backend + readiness

Làm theo docs/prompts/README.md mục "Quy tắc chung".
Phụ thuộc phải xong trước: P010, P003. Kiểm tra bảng Tiến độ trong docs/prompts/README.md; nếu chưa xong thì dừng và báo tôi.

Đọc trước:
- docs/steps/TRANG-THAI.md
- docs/implementation-plan.vi.md §24 (bảng quyết định)
- docs/features/F00-nen-tang-desktop/be.md (mục B, E)
- be/src/writestory_be/bootstrap/protocol.py

Việc cần làm:
1. `src/backend.rs`: sinh token 32 byte; spawn (dev: `uv run python -m writestory_be` tại gốc repo; release để P018); ghi BootstrapConfig một dòng vào stdin và giữ stdin mở; đọc NDJSON progress/ready/fatal; drain stderr ra logs/backend-stderr.log + ring buffer; health check; theo dõi exit → backend_crashed.
2. `src/win_job.rs`: Job Object KILL_ON_JOB_CLOSE (Windows).
3. Unit test parse NDJSON (ready/progress/fatal, dòng rác bỏ qua).

Phạm vi file: desktop/src-tauri/src/
Xong khi: `tauri dev` tự khởi động backend tới phase ready; `cargo test` pass.

Kết thúc: tick các mục đã làm trong checklist spec liên quan; đổi trạng thái P011 thành done trong bảng Tiến độ của docs/prompts/README.md (đọc lại file ngay trước khi sửa, chỉ sửa dòng P011); cập nhật docs/steps/TRANG-THAI.md; báo cáo theo Quy tắc chung mục 8.
```
