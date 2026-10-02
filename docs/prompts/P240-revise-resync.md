# P240 – BE: job sửa + stale_from + resync

| Làn | Tính năng | Phụ thuộc |
|---|---|---|
| BE | F11 | [P239](./P239-findings-api.md), [P221](./P221-revise-workflow.md) |

Dán nguyên khối dưới vào một cửa sổ Claude Code mới mở tại `E:\pm\WriteStoryApp`. Trạng thái của prompt được theo dõi trong [README.md](./README.md#tiến-độ).

```text
[P240] BE: job sửa + stale_from + resync

Làm theo docs/prompts/README.md mục "Quy tắc chung".
Phụ thuộc phải xong trước: P239, P221. Kiểm tra bảng Tiến độ trong docs/prompts/README.md; nếu chưa xong thì dừng và báo tôi.

Đọc trước:
- docs/steps/TRANG-THAI.md
- docs/implementation-plan.vi.md §24 (bảng quyết định)
- docs/features/F11-candidate-review-va-sua/be.md
- docs/implementation-plan.vi.md FL07, §24 D12
- docs/tests/flows/T10-sua-tay-va-resync.md

Việc cần làm:
1. Job revise (gọi P221), sửa chương mới nhất → stale_from(N) resettle; chương cũ → stale_from(K).
2. Job resync tuần tự K..N từ snapshot K-1 (POST /v1/works/{id}/resync, dry_run).
3. Test T10 phần BE.

Phạm vi file: be/src/writestory_be/modules/longform/, be/tests/
Xong khi: Test pass.

Kết thúc: tick các mục đã làm trong checklist spec liên quan; đổi trạng thái P240 thành done trong bảng Tiến độ của docs/prompts/README.md (đọc lại file ngay trước khi sửa, chỉ sửa dòng P240); cập nhật docs/steps/TRANG-THAI.md; báo cáo theo Quy tắc chung mục 8.
```
