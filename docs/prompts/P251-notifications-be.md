# P251 – BE: notification outbox + event

| Làn | Tính năng | Phụ thuộc |
|---|---|---|
| BE | F14 | [P108](./P108-eventbus-db.md) |

Dán nguyên khối dưới vào một cửa sổ Claude Code mới mở tại `E:\pm\WriteStoryApp`. Trạng thái của prompt được theo dõi trong [README.md](./README.md#tiến-độ).

```text
[P251] BE: notification outbox + event

Làm theo docs/prompts/README.md mục "Quy tắc chung".
Phụ thuộc phải xong trước: P108. Kiểm tra bảng Tiến độ trong docs/prompts/README.md; nếu chưa xong thì dừng và báo tôi.

Đọc trước:
- docs/steps/TRANG-THAI.md
- docs/implementation-plan.vi.md §24 (bảng quyết định)
- docs/features/F14-thong-bao-nhat-ky-chi-phi/be.md
- docs/implementation-plan.vi.md §24 D5

Việc cần làm:
1. Migration notification_outbox; tạo thông báo khi chương bị chặn, batch xong, provider lỗi kéo dài; event notification.created.
2. GET /v1/notifications, read, read-all; GET/PUT /v1/settings/notifications.
3. Test.

Phạm vi file: be/src/writestory_be/modules/operations/notifications*, be/migrations/versions/, be/tests/
Xong khi: Test pass.

Kết thúc: tick các mục đã làm trong checklist spec liên quan; đổi trạng thái P251 thành done trong bảng Tiến độ của docs/prompts/README.md (đọc lại file ngay trước khi sửa, chỉ sửa dòng P251); cập nhật docs/steps/TRANG-THAI.md; báo cáo theo Quy tắc chung mục 8.
```
