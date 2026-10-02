# P154 – FE: event bus toàn cục + banner kết nối

| Làn | Tính năng | Phụ thuộc |
|---|---|---|
| FE | F01 | [P152](./P152-app-shell.md) |

Dán nguyên khối dưới vào một cửa sổ Claude Code mới mở tại `E:\pm\WriteStoryApp`. Trạng thái của prompt được theo dõi trong [README.md](./README.md#tiến-độ).

```text
[P154] FE: event bus toàn cục + banner kết nối

Làm theo docs/prompts/README.md mục "Quy tắc chung".
Phụ thuộc phải xong trước: P152. Kiểm tra bảng Tiến độ trong docs/prompts/README.md; nếu chưa xong thì dừng và báo tôi.

Đọc trước:
- docs/steps/TRANG-THAI.md
- docs/implementation-plan.vi.md §24 (bảng quyết định)
- docs/features/F01-hop-dong-api-va-su-kien/fe.md
- docs/ui-design.vi.md §6

Việc cần làm:
1. `features/jobs/eventBus.ts`: một kết nối /v1/events cho cả app (dùng shared/api/sse.ts), store Zustand theo work_id, gom token.delta 50–100 ms, xử lý replay_gap (invalidate query).
2. Banner mất kết nối + tự nối lại.
3. Hook useWorkEvents, useConnectionState; test với stream giả.

Phạm vi file: fe/src/features/jobs/, fe/src/app/
Xong khi: test pass.

Kết thúc: tick các mục đã làm trong checklist spec liên quan; đổi trạng thái P154 thành done trong bảng Tiến độ của docs/prompts/README.md (đọc lại file ngay trước khi sửa, chỉ sửa dòng P154); cập nhật docs/steps/TRANG-THAI.md; báo cáo theo Quy tắc chung mục 8.
```
