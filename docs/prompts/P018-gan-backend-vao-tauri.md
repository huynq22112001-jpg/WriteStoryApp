# P018 – Gắn backend vào bundle Tauri + installer Windows

| Làn | Tính năng | Phụ thuộc |
|---|---|---|
| DESKTOP | F00 / S09 | [P017](./P017-pyinstaller-onedir.md), [P012](./P012-rust-shutdown-commands.md) |

Dán nguyên khối dưới vào một cửa sổ Claude Code mới mở tại `E:\pm\WriteStoryApp`. Trạng thái của prompt được theo dõi trong [README.md](./README.md#tiến-độ).

```text
[P018] Gắn backend vào bundle Tauri + installer Windows

Làm theo docs/prompts/README.md mục "Quy tắc chung".
Phụ thuộc phải xong trước: P017, P012. Kiểm tra bảng Tiến độ trong docs/prompts/README.md; nếu chưa xong thì dừng và báo tôi.

Đọc trước:
- docs/steps/TRANG-THAI.md
- docs/implementation-plan.vi.md §24 (bảng quyết định)
- docs/steps/S09-dong-goi-backend.md
- docs/review-and-optimization.vi.md §7.1

Việc cần làm:
1. tauri.conf.json: bundle.resources dạng thư mục `resources/backend/`; backend.rs bản release spawn binary trong resource_dir.
2. Build installer NSIS, webviewInstallMode offlineInstaller.
3. Đo dung lượng bundle, thời gian mở app tới ready, RAM idle; ghi vào `docs/adr/ADR-002-spawn-backend.md`.

Phạm vi file: desktop/src-tauri/, docs/adr/
Xong khi: Installer chạy được trên máy không có uv/Python (báo trung thực nếu chưa thử được).

Kết thúc: tick các mục đã làm trong checklist spec liên quan; đổi trạng thái P018 thành done trong bảng Tiến độ của docs/prompts/README.md (đọc lại file ngay trước khi sửa, chỉ sửa dòng P018); cập nhật docs/steps/TRANG-THAI.md; báo cáo theo Quy tắc chung mục 8.
```
