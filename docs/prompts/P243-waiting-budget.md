# P243 – BE: lý do chờ + ngân sách

| Làn | Tính năng | Phụ thuộc |
|---|---|---|
| BE | F12 | [P242](./P242-scheduler-fair.md) |

Dán nguyên khối dưới vào một cửa sổ Claude Code mới mở tại `E:\pm\WriteStoryApp`. Trạng thái của prompt được theo dõi trong [README.md](./README.md#tiến-độ).

```text
[P243] BE: lý do chờ + ngân sách

Làm theo docs/prompts/README.md mục "Quy tắc chung".
Phụ thuộc phải xong trước: P242. Kiểm tra bảng Tiến độ trong docs/prompts/README.md; nếu chưa xong thì dừng và báo tôi.

Đọc trước:
- docs/steps/TRANG-THAI.md
- docs/implementation-plan.vi.md §24 (bảng quyết định)
- docs/features/F12-auto-write-da-truyen/be.md
- docs/implementation-plan.vi.md §23.2 #7 #8, §24 D9, D14

Việc cần làm:
1. waiting_slot với wait_reason: WORKER_POOL_FULL, PROVIDER_CONCURRENCY_FULL, PROVIDER_RATE_LIMIT, BUDGET_EXCEEDED, WORK_BUSY_QUEUED, VAULT_LOCKED, PROVIDER_UNREACHABLE (backoff tới 5 phút).
2. `jobs/budget.py`: ngân sách ngày/truyện theo timezone.
3. Test: 429 + Retry-After chờ đúng; hết ngân sách; vault khóa rồi mở thì chạy tiếp; một truyện bị chặn không ảnh hưởng truyện khác.

Phạm vi file: be/src/writestory_be/jobs/, be/tests/
Xong khi: Test pass.

Kết thúc: tick các mục đã làm trong checklist spec liên quan; đổi trạng thái P243 thành done trong bảng Tiến độ của docs/prompts/README.md (đọc lại file ngay trước khi sửa, chỉ sửa dòng P243); cập nhật docs/steps/TRANG-THAI.md; báo cáo theo Quy tắc chung mục 8.
```
