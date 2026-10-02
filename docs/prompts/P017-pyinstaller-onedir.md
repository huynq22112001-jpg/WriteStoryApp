# P017 – PyInstaller onedir cho backend

| Làn | Tính năng | Phụ thuộc |
|---|---|---|
| DESKTOP | F00 / S09 | [P003](./P003-kiem-chung-be-base.md) |

Dán nguyên khối dưới vào một cửa sổ Claude Code mới mở tại `E:\pm\WriteStoryApp`. Trạng thái của prompt được theo dõi trong [README.md](./README.md#tiến-độ).

```text
[P017] PyInstaller onedir cho backend

Làm theo docs/prompts/README.md mục "Quy tắc chung".
Phụ thuộc phải xong trước: P003. Kiểm tra bảng Tiến độ trong docs/prompts/README.md; nếu chưa xong thì dừng và báo tôi.

Đọc trước:
- docs/steps/TRANG-THAI.md
- docs/implementation-plan.vi.md §24 (bảng quyết định)
- docs/steps/S09-dong-goi-backend.md
- docs/features/F00-nen-tang-desktop/be.md (mục F)
- docs/implementation-plan.vi.md §24 D22, D23

Việc cần làm:
1. `tools/packaging/backend.spec`: onedir, tên writestory-backend, console=True, collect_data_files('writestory_ai'), hidden import aiosqlite.
2. `tools/packaging/build_backend.py`: uv sync --frozen → pyinstaller → copy vào desktop/src-tauri/resources/backend/.
3. Chạy binary tạo ra với một dòng BootstrapConfig qua stdin → nhận ready.

Phạm vi file: tools/packaging/, be/pyproject.toml (nhóm build nếu cần)
Xong khi: Binary onedir chạy được và in ready.

Kết thúc: tick các mục đã làm trong checklist spec liên quan; đổi trạng thái P017 thành done trong bảng Tiến độ của docs/prompts/README.md (đọc lại file ngay trước khi sửa, chỉ sửa dòng P017); cập nhật docs/steps/TRANG-THAI.md; báo cáo theo Quy tắc chung mục 8.
```
