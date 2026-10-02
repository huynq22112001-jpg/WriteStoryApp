# P236 – BE: cổng vào + commit một transaction

| Làn | Tính năng | Phụ thuộc |
|---|---|---|
| BE | F10 | [P235](./P235-write-job-runner.md) |

Dán nguyên khối dưới vào một cửa sổ Claude Code mới mở tại `E:\pm\WriteStoryApp`. Trạng thái của prompt được theo dõi trong [README.md](./README.md#tiến-độ).

```text
[P236] BE: cổng vào + commit một transaction

Làm theo docs/prompts/README.md mục "Quy tắc chung".
Phụ thuộc phải xong trước: P235. Kiểm tra bảng Tiến độ trong docs/prompts/README.md; nếu chưa xong thì dừng và báo tôi.

Đọc trước:
- docs/steps/TRANG-THAI.md
- docs/implementation-plan.vi.md §24 (bảng quyết định)
- docs/features/F10-viet-chuong-lien-mach/be.md
- docs/implementation-plan.vi.md §6.2, §24 D6, D8, D11

Việc cần làm:
1. Cổng vào: chương N-1 committed + state_applied + continuity_status = ok.
2. Commit một transaction: revision + story_state + handoff(N) + summary + hooks + timeline + FTS + job result + events.
3. Không commit khi state không hợp lệ; repair_exhausted → waiting_user + blocked_needs_resync; job đơn lẻ từ AI panel dừng waiting_user (review_required).
4. Test: 5 chương liên tiếp, chương 3 seam fail rồi sửa được, 0 chương state_applied=false.

Phạm vi file: be/src/writestory_be/modules/longform/, be/tests/
Xong khi: Test pass.

Kết thúc: tick các mục đã làm trong checklist spec liên quan; đổi trạng thái P236 thành done trong bảng Tiến độ của docs/prompts/README.md (đọc lại file ngay trước khi sửa, chỉ sửa dòng P236); cập nhật docs/steps/TRANG-THAI.md; báo cáo theo Quy tắc chung mục 8.
```
