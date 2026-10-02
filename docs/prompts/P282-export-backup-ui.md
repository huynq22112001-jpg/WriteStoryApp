# P282 – FE: hộp thoại xuất + trang sao lưu

| Làn | Tính năng | Phụ thuộc |
|---|---|---|
| FE | F13 | [P153](./P153-error-empty-states.md) |

Dán nguyên khối dưới vào một cửa sổ Claude Code mới mở tại `E:\pm\WriteStoryApp`. Trạng thái của prompt được theo dõi trong [README.md](./README.md#tiến-độ).

```text
[P282] FE: hộp thoại xuất + trang sao lưu

Làm theo docs/prompts/README.md mục "Quy tắc chung".
Phụ thuộc phải xong trước: P153. Kiểm tra bảng Tiến độ trong docs/prompts/README.md; nếu chưa xong thì dừng và báo tôi.

Đọc trước:
- docs/steps/TRANG-THAI.md
- docs/implementation-plan.vi.md §24 (bảng quyết định)
- docs/features/F13-xuat-va-sao-luu/fe.md

Việc cần làm:
1. Hộp thoại export (định dạng, khoảng chương, metadata, tiêu đề chương), danh sách bản xuất.
2. /settings/data: sao lưu, danh sách, kiểm tra, khôi phục (xác nhận 2 bước).
3. Test.

Phạm vi file: fe/src/features/export/, fe/src/features/backup/
Xong khi: test pass.

Kết thúc: tick các mục đã làm trong checklist spec liên quan; đổi trạng thái P282 thành done trong bảng Tiến độ của docs/prompts/README.md (đọc lại file ngay trước khi sửa, chỉ sửa dòng P282); cập nhật docs/steps/TRANG-THAI.md; báo cáo theo Quy tắc chung mục 8.
```
