# P012 – Rust: tắt sạch + commands cho FE

| Làn | Tính năng | Phụ thuộc |
|---|---|---|
| DESKTOP | F00 | [P011](./P011-rust-spawn-backend.md) |

Dán nguyên khối dưới vào một cửa sổ Claude Code mới mở tại `E:\pm\WriteStoryApp`. Trạng thái của prompt được theo dõi trong [README.md](./README.md#tiến-độ).

```text
[P012] Rust: tắt sạch + commands cho FE

Làm theo docs/prompts/README.md mục "Quy tắc chung".
Phụ thuộc phải xong trước: P011. Kiểm tra bảng Tiến độ trong docs/prompts/README.md; nếu chưa xong thì dừng và báo tôi.

Đọc trước:
- docs/steps/TRANG-THAI.md
- docs/implementation-plan.vi.md §24 (bảng quyết định)
- docs/features/F00-nen-tang-desktop/be.md (mục D, bảng commands)
- docs/review-and-optimization.vi.md §7.1

Việc cần làm:
1. Xử lý RunEvent::ExitRequested (prevent_exit → POST /v1/system/shutdown → chờ → kill) và RunEvent::Exit.
2. `src/commands.rs`: get_boot_state, pick_data_root_folder, confirm_data_root, get_backend_session, restart_backend, open_logs_folder, quit_app; khai báo trong capability.
3. Thử: đóng cửa sổ → không còn tiến trình backend; kill app (Windows) → backend chết theo.

Phạm vi file: desktop/src-tauri/
Xong khi: Hai phép thử cuối đạt (ghi kết quả).

Kết thúc: tick các mục đã làm trong checklist spec liên quan; đổi trạng thái P012 thành done trong bảng Tiến độ của docs/prompts/README.md (đọc lại file ngay trước khi sửa, chỉ sửa dòng P012); cập nhật docs/steps/TRANG-THAI.md; báo cáo theo Quy tắc chung mục 8.
```
