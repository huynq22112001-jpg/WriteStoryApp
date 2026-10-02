# P244 – BE: API auto-write 3 chế độ

| Làn | Tính năng | Phụ thuộc |
|---|---|---|
| BE | F12 | [P243](./P243-waiting-budget.md) |

Dán nguyên khối dưới vào một cửa sổ Claude Code mới mở tại `E:\pm\WriteStoryApp`. Trạng thái của prompt được theo dõi trong [README.md](./README.md#tiến-độ).

```text
[P244] BE: API auto-write 3 chế độ

Làm theo docs/prompts/README.md mục "Quy tắc chung".
Phụ thuộc phải xong trước: P243. Kiểm tra bảng Tiến độ trong docs/prompts/README.md; nếu chưa xong thì dừng và báo tôi.

Đọc trước:
- docs/steps/TRANG-THAI.md
- docs/implementation-plan.vi.md §24 (bảng quyết định)
- docs/features/F12-auto-write-da-truyen/be.md
- docs/implementation-plan.vi.md §4.2 (chế độ), FL05, §24 D13
- docs/tests/flows/T07-auto-write-mot-truyen.md

Việc cần làm:
1. POST /v1/works/{id}/autowrite {target_chapter|count, mode auto|review_each|review_every_k, priority}, pause {when: after_chapter|for_edit}, resume, cancel.
2. Chỉ enqueue chương N+1 sau khi N commit; ghim cấu hình theo từng job chương.
3. Test T07 phần BE.

Phạm vi file: be/src/writestory_be/modules/autowrite/, be/tests/
Xong khi: Test pass.

Kết thúc: tick các mục đã làm trong checklist spec liên quan; đổi trạng thái P244 thành done trong bảng Tiến độ của docs/prompts/README.md (đọc lại file ngay trước khi sửa, chỉ sửa dòng P244); cập nhật docs/steps/TRANG-THAI.md; báo cáo theo Quy tắc chung mục 8.
```
