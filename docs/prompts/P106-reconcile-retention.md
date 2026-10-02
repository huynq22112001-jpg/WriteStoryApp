# P106 – Reconcile khi khởi động + retention

| Làn | Tính năng | Phụ thuộc |
|---|---|---|
| BE | F02 | [P105](./P105-work-locks.md) |

Dán nguyên khối dưới vào một cửa sổ Claude Code mới mở tại `E:\pm\WriteStoryApp`. Trạng thái của prompt được theo dõi trong [README.md](./README.md#tiến-độ).

```text
[P106] Reconcile khi khởi động + retention

Làm theo docs/prompts/README.md mục "Quy tắc chung".
Phụ thuộc phải xong trước: P105. Kiểm tra bảng Tiến độ trong docs/prompts/README.md; nếu chưa xong thì dừng và báo tôi.

Đọc trước:
- docs/steps/TRANG-THAI.md
- docs/implementation-plan.vi.md §24 (bảng quyết định)
- docs/features/F02-nen-du-lieu/be.md
- docs/tests/flows/T09-huy-crash-va-phuc-hoi.md

Việc cần làm:
1. register_reconciler / run_startup_reconcile: job running → interrupted, phát backend.notice jobs_interrupted.
2. `retention.py`: xóa job_events > 90 ngày, idempotency hết hạn, theo lô.
3. Test mô phỏng crash: job đang running sau restart thành interrupted.

Phạm vi file: be/src/writestory_be/infrastructure/db/, be/src/writestory_be/jobs/, be/tests/
Xong khi: Test pass.

Kết thúc: tick các mục đã làm trong checklist spec liên quan; đổi trạng thái P106 thành done trong bảng Tiến độ của docs/prompts/README.md (đọc lại file ngay trước khi sửa, chỉ sửa dòng P106); cập nhật docs/steps/TRANG-THAI.md; báo cáo theo Quy tắc chung mục 8.
```
