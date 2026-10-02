# P108 – EventBus lưu DB + replay

| Làn | Tính năng | Phụ thuộc |
|---|---|---|
| BE | F01 | [P104](./P104-writer-queue-uow.md) |

Dán nguyên khối dưới vào một cửa sổ Claude Code mới mở tại `E:\pm\WriteStoryApp`. Trạng thái của prompt được theo dõi trong [README.md](./README.md#tiến-độ).

```text
[P108] EventBus lưu DB + replay

Làm theo docs/prompts/README.md mục "Quy tắc chung".
Phụ thuộc phải xong trước: P104. Kiểm tra bảng Tiến độ trong docs/prompts/README.md; nếu chưa xong thì dừng và báo tôi.

Đọc trước:
- docs/steps/TRANG-THAI.md
- docs/implementation-plan.vi.md §24 (bảng quyết định)
- docs/features/F01-hop-dong-api-va-su-kien/be.md (mục C)
- docs/implementation-plan.vi.md §23.1.C

Việc cần làm:
1. `jobs/events.py` chế độ DB: event lưu qua UnitOfWork.add_event, broadcast sau commit; replay từ DB khi nối lại; giữ RAM cho token.delta.
2. replay_gap khi since cũ hơn retention.
3. Test: event chỉ phát sau commit, rollback không phát; nối lại bằng Last-Event-ID nhận đủ.

Phạm vi file: be/src/writestory_be/jobs/, be/src/writestory_be/api/streams.py, be/tests/
Xong khi: Test pass.

Kết thúc: tick các mục đã làm trong checklist spec liên quan; đổi trạng thái P108 thành done trong bảng Tiến độ của docs/prompts/README.md (đọc lại file ngay trước khi sửa, chỉ sửa dòng P108); cập nhật docs/steps/TRANG-THAI.md; báo cáo theo Quy tắc chung mục 8.
```
