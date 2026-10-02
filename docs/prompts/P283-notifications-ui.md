# P283 – FE: trung tâm thông báo + thông báo native

| Làn | Tính năng | Phụ thuộc |
|---|---|---|
| FE | F14 | [P154](./P154-event-bus-fe.md) |

Dán nguyên khối dưới vào một cửa sổ Claude Code mới mở tại `E:\pm\WriteStoryApp`. Trạng thái của prompt được theo dõi trong [README.md](./README.md#tiến-độ).

```text
[P283] FE: trung tâm thông báo + thông báo native

Làm theo docs/prompts/README.md mục "Quy tắc chung".
Phụ thuộc phải xong trước: P154. Kiểm tra bảng Tiến độ trong docs/prompts/README.md; nếu chưa xong thì dừng và báo tôi.

Đọc trước:
- docs/steps/TRANG-THAI.md
- docs/implementation-plan.vi.md §24 (bảng quyết định)
- docs/features/F14-thong-bao-nhat-ky-chi-phi/fe.md

Việc cần làm:
1. Trung tâm thông báo (bấm mở đúng chỗ xử lý), /settings/notifications.
2. Nhận event notification.created → gọi plugin notification của Tauri khi chạy desktop.
3. Test.

Phạm vi file: fe/src/features/notifications/
Xong khi: test pass.

Kết thúc: tick các mục đã làm trong checklist spec liên quan; đổi trạng thái P283 thành done trong bảng Tiến độ của docs/prompts/README.md (đọc lại file ngay trước khi sửa, chỉ sửa dòng P283); cập nhật docs/steps/TRANG-THAI.md; báo cáo theo Quy tắc chung mục 8.
```
