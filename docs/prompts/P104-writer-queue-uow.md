# P104 – Writer queue + UnitOfWork

| Làn | Tính năng | Phụ thuộc |
|---|---|---|
| BE | F02 | [P102](./P102-migration-baseline.md) |

Dán nguyên khối dưới vào một cửa sổ Claude Code mới mở tại `E:\pm\WriteStoryApp`. Trạng thái của prompt được theo dõi trong [README.md](./README.md#tiến-độ).

```text
[P104] Writer queue + UnitOfWork

Làm theo docs/prompts/README.md mục "Quy tắc chung".
Phụ thuộc phải xong trước: P102. Kiểm tra bảng Tiến độ trong docs/prompts/README.md; nếu chưa xong thì dừng và báo tôi.

Đọc trước:
- docs/steps/TRANG-THAI.md
- docs/implementation-plan.vi.md §24 (bảng quyết định)
- docs/features/F02-nen-du-lieu/be.md (WriterQueue, UnitOfWork, assert_not_in_write_txn)
- docs/implementation-plan.vi.md §4.2

Việc cần làm:
1. `infrastructure/db/writer.py`: một task asyncio nhận lệnh commit; quá hạn → AppError DB_BUSY.
2. `unit_of_work.py`: UnitOfWork + `add_event()` (outbox job_events cùng transaction, để P108 dùng).
3. `guards.py`: assert_not_in_write_txn() gọi trước mọi lời gọi AI.
4. Test: 20 coroutine commit đồng thời không lỗi 'database is locked'; rollback không để lại event.

Phạm vi file: be/src/writestory_be/infrastructure/db/, be/tests/
Xong khi: Test pass.

Kết thúc: tick các mục đã làm trong checklist spec liên quan; đổi trạng thái P104 thành done trong bảng Tiến độ của docs/prompts/README.md (đọc lại file ngay trước khi sửa, chỉ sửa dòng P104); cập nhật docs/steps/TRANG-THAI.md; báo cáo theo Quy tắc chung mục 8.
```
