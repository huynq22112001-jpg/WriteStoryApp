# P105 – Khóa truyện có lease + heartbeat

| Làn | Tính năng | Phụ thuộc |
|---|---|---|
| BE | F02 | [P104](./P104-writer-queue-uow.md) |

Dán nguyên khối dưới vào một cửa sổ Claude Code mới mở tại `E:\pm\WriteStoryApp`. Trạng thái của prompt được theo dõi trong [README.md](./README.md#tiến-độ).

```text
[P105] Khóa truyện có lease + heartbeat

Làm theo docs/prompts/README.md mục "Quy tắc chung".
Phụ thuộc phải xong trước: P104. Kiểm tra bảng Tiến độ trong docs/prompts/README.md; nếu chưa xong thì dừng và báo tôi.

Đọc trước:
- docs/steps/TRANG-THAI.md
- docs/implementation-plan.vi.md §24 (bảng quyết định)
- docs/features/F02-nen-du-lieu/be.md (WorkLockManager)
- docs/implementation-plan.vi.md §4.2, §24 D15

Việc cần làm:
1. Migration `0002_f02_work_locks` (owner_id, lease_expires_at, heartbeat_at).
2. WorkLockManager: xếp hàng (không fail-fast), heartbeat, LockLost khi mất lease, lấy lại lock hết hạn.
3. Test: hai job cùng truyện → job sau chờ; lease hết → job khác lấy được.

Phạm vi file: be/src/writestory_be/infrastructure/db/, be/migrations/versions/, be/tests/
Xong khi: Test pass.

Kết thúc: tick các mục đã làm trong checklist spec liên quan; đổi trạng thái P105 thành done trong bảng Tiến độ của docs/prompts/README.md (đọc lại file ngay trước khi sửa, chỉ sửa dòng P105); cập nhật docs/steps/TRANG-THAI.md; báo cáo theo Quy tắc chung mục 8.
```
