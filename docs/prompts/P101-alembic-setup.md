# P101 – Cài đặt Alembic async

| Làn | Tính năng | Phụ thuộc |
|---|---|---|
| BE | F02 | [P003](./P003-kiem-chung-be-base.md) |

Dán nguyên khối dưới vào một cửa sổ Claude Code mới mở tại `E:\pm\WriteStoryApp`. Trạng thái của prompt được theo dõi trong [README.md](./README.md#tiến-độ).

```text
[P101] Cài đặt Alembic async

Làm theo docs/prompts/README.md mục "Quy tắc chung".
Phụ thuộc phải xong trước: P003. Kiểm tra bảng Tiến độ trong docs/prompts/README.md; nếu chưa xong thì dừng và báo tôi.

Đọc trước:
- docs/steps/TRANG-THAI.md
- docs/implementation-plan.vi.md §24 (bảng quyết định)
- docs/features/F02-nen-du-lieu/be.md
- docs/implementation-plan.vi.md §5

Việc cần làm:
1. `be/alembic.ini`, `be/migrations/env.py` async, đọc đường dẫn DB từ data-root, `render_as_batch=True`.
2. `be/src/writestory_be/infrastructure/db/base.py` (DeclarativeBase, quy ước tên constraint).
3. Test: tạo DB trống trên data-root tạm, `upgrade head` chạy được khi chưa có migration nào.

Phạm vi file: be/alembic.ini, be/migrations/, be/src/writestory_be/infrastructure/db/
Xong khi: Test pass.

Kết thúc: tick các mục đã làm trong checklist spec liên quan; đổi trạng thái P101 thành done trong bảng Tiến độ của docs/prompts/README.md (đọc lại file ngay trước khi sửa, chỉ sửa dòng P101); cập nhật docs/steps/TRANG-THAI.md; báo cáo theo Quy tắc chung mục 8.
```
