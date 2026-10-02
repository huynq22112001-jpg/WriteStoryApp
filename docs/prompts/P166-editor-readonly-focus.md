# P166 – FE: chương nền chỉ đọc + chế độ tập trung

| Làn | Tính năng | Phụ thuộc |
|---|---|---|
| FE | F07 | [P165](./P165-editor-autosave.md) |

Dán nguyên khối dưới vào một cửa sổ Claude Code mới mở tại `E:\pm\WriteStoryApp`. Trạng thái của prompt được theo dõi trong [README.md](./README.md#tiến-độ).

```text
[P166] FE: chương nền chỉ đọc + chế độ tập trung

Làm theo docs/prompts/README.md mục "Quy tắc chung".
Phụ thuộc phải xong trước: P165. Kiểm tra bảng Tiến độ trong docs/prompts/README.md; nếu chưa xong thì dừng và báo tôi.

Đọc trước:
- docs/steps/TRANG-THAI.md
- docs/implementation-plan.vi.md §24 (bảng quyết định)
- docs/features/F07-editor-va-phien-ban/fe.md
- docs/implementation-plan.vi.md §23.2 #3

Việc cần làm:
1. Khi chương là nền cho chương đang viết: editor read-only + nút 'Tạm dừng để sửa' (gọi autowrite pause reason edit_base).
2. Chế độ tập trung Ctrl+Shift+F.
3. Test.

Phạm vi file: fe/src/features/editor/
Xong khi: test pass.

Kết thúc: tick các mục đã làm trong checklist spec liên quan; đổi trạng thái P166 thành done trong bảng Tiến độ của docs/prompts/README.md (đọc lại file ngay trước khi sửa, chỉ sửa dòng P166); cập nhật docs/steps/TRANG-THAI.md; báo cáo theo Quy tắc chung mục 8.
```
