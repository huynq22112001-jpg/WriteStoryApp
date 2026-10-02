# P242 – BE: scheduler đa truyện xoay vòng công bằng

| Làn | Tính năng | Phụ thuộc |
|---|---|---|
| BE | F12 | [P236](./P236-commit-gate.md) |

Dán nguyên khối dưới vào một cửa sổ Claude Code mới mở tại `E:\pm\WriteStoryApp`. Trạng thái của prompt được theo dõi trong [README.md](./README.md#tiến-độ).

```text
[P242] BE: scheduler đa truyện xoay vòng công bằng

Làm theo docs/prompts/README.md mục "Quy tắc chung".
Phụ thuộc phải xong trước: P236. Kiểm tra bảng Tiến độ trong docs/prompts/README.md; nếu chưa xong thì dừng và báo tôi.

Đọc trước:
- docs/steps/TRANG-THAI.md
- docs/implementation-plan.vi.md §24 (bảng quyết định)
- docs/features/F12-auto-write-da-truyen/be.md (thuật toán scheduler)
- docs/implementation-plan.vi.md §4.2
- docs/review-and-optimization.vi.md §2.3 (lỗi slice(0,N))
- docs/tests/flows/T08-da-truyen-dong-thoi.md

Việc cần làm:
1. Migration work_queues (mode, priority, weight, current_weight, target…).
2. `jobs/scheduler.py`: ready set, xoay vòng có trọng số, tối đa 1 job ghi mỗi truyện, worker pool cấu hình (mặc định 4).
3. Test: 5 truyện × 5 chương mock song song, không truyện nào bị bỏ đói (kèm test đối chứng slice(0,N) thất bại).

Phạm vi file: be/src/writestory_be/jobs/, be/migrations/versions/, be/tests/
Xong khi: Test pass.

Kết thúc: tick các mục đã làm trong checklist spec liên quan; đổi trạng thái P242 thành done trong bảng Tiến độ của docs/prompts/README.md (đọc lại file ngay trước khi sửa, chỉ sửa dòng P242); cập nhật docs/steps/TRANG-THAI.md; báo cáo theo Quy tắc chung mục 8.
```
