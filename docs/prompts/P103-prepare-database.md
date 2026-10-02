# P103 – Hook prepare_database khi khởi động

| Làn | Tính năng | Phụ thuộc |
|---|---|---|
| BE | F02 | [P102](./P102-migration-baseline.md) |

Dán nguyên khối dưới vào một cửa sổ Claude Code mới mở tại `E:\pm\WriteStoryApp`. Trạng thái của prompt được theo dõi trong [README.md](./README.md#tiến-độ).

```text
[P103] Hook prepare_database khi khởi động

Làm theo docs/prompts/README.md mục "Quy tắc chung".
Phụ thuộc phải xong trước: P102. Kiểm tra bảng Tiến độ trong docs/prompts/README.md; nếu chưa xong thì dừng và báo tôi.

Đọc trước:
- docs/steps/TRANG-THAI.md
- docs/implementation-plan.vi.md §24 (bảng quyết định)
- docs/features/F02-nen-du-lieu/be.md
- docs/features/F00-nen-tang-desktop/be.md (mục B.8)
- docs/implementation-plan.vi.md §24 D1

Việc cần làm:
1. `infrastructure/db/migrations.py` prepare_database(config, progress_cb): backup trước migrate bằng VACUUM INTO vào data/backups/pre-migrate-<ts>/, migrate, lỗi SCHEMA_TOO_NEW / MIGRATION_FAILED / DB_MISSING (marker báo đã khởi tạo mà thiếu file).
2. Gọi trong `bootstrap/runtime.py` trước khi bind, phát progress 'migrating'.
3. `/v1/health` trả schema_version = revision hiện tại.
4. Test các nhánh lỗi.

Phạm vi file: be/src/writestory_be/infrastructure/db/, bootstrap/runtime.py, modules/system/router.py, be/tests/
Xong khi: Test pass; khởi động lần 2 không migrate lại.

Kết thúc: tick các mục đã làm trong checklist spec liên quan; đổi trạng thái P103 thành done trong bảng Tiến độ của docs/prompts/README.md (đọc lại file ngay trước khi sửa, chỉ sửa dòng P103); cập nhật docs/steps/TRANG-THAI.md; báo cáo theo Quy tắc chung mục 8.
```
