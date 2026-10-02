# P241 – BE: chèn/xóa/sắp xếp chương giữa truyện

| Làn | Tính năng | Phụ thuộc |
|---|---|---|
| BE | F11 | [P240](./P240-revise-resync.md) |

Dán nguyên khối dưới vào một cửa sổ Claude Code mới mở tại `E:\pm\WriteStoryApp`. Trạng thái của prompt được theo dõi trong [README.md](./README.md#tiến-độ).

```text
[P241] BE: chèn/xóa/sắp xếp chương giữa truyện

Làm theo docs/prompts/README.md mục "Quy tắc chung".
Phụ thuộc phải xong trước: P240. Kiểm tra bảng Tiến độ trong docs/prompts/README.md; nếu chưa xong thì dừng và báo tôi.

Đọc trước:
- docs/steps/TRANG-THAI.md
- docs/implementation-plan.vi.md §24 (bảng quyết định)
- docs/features/F11-candidate-review-va-sua/be.md
- docs/implementation-plan.vi.md §23.2 #4

Việc cần làm:
1. Khi truyện dừng: chèn/xóa/sắp xếp tạo stale_from(K nhỏ nhất bị ảnh hưởng); đang chạy → CHAPTER_RANGE_CONFLICT; xóa chương mới nhất vào thùng rác + rollback state.
2. Test.

Phạm vi file: be/src/writestory_be/modules/chapters/, modules/longform/, be/tests/
Xong khi: Test pass.

Kết thúc: tick các mục đã làm trong checklist spec liên quan; đổi trạng thái P241 thành done trong bảng Tiến độ của docs/prompts/README.md (đọc lại file ngay trước khi sửa, chỉ sửa dòng P241); cập nhật docs/steps/TRANG-THAI.md; báo cáo theo Quy tắc chung mục 8.
```
