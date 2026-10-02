# P270 – FE: cài đặt ngôn ngữ + style profile

| Làn | Tính năng | Phụ thuộc |
|---|---|---|
| FE | F08 | [P153](./P153-error-empty-states.md) |

Dán nguyên khối dưới vào một cửa sổ Claude Code mới mở tại `E:\pm\WriteStoryApp`. Trạng thái của prompt được theo dõi trong [README.md](./README.md#tiến-độ).

```text
[P270] FE: cài đặt ngôn ngữ + style profile

Làm theo docs/prompts/README.md mục "Quy tắc chung".
Phụ thuộc phải xong trước: P153. Kiểm tra bảng Tiến độ trong docs/prompts/README.md; nếu chưa xong thì dừng và báo tôi.

Đọc trước:
- docs/steps/TRANG-THAI.md
- docs/implementation-plan.vi.md §24 (bảng quyết định)
- docs/features/F08-goi-ngon-ngu-vi/fe.md

Việc cần làm:
1. /settings/language (MVP chỉ 'Tiếng Việt'), /works/$workId/bible/style: kiểu bỏ dấu, lớp từ, kiểu thoại, dấu câu, danh sách cụm cấm, đoạn mẫu giọng văn.
2. Hiển thị finding tiếng Việt theo message_key.
3. Test.

Phạm vi file: fe/src/features/language/
Xong khi: test pass.

Kết thúc: tick các mục đã làm trong checklist spec liên quan; đổi trạng thái P270 thành done trong bảng Tiến độ của docs/prompts/README.md (đọc lại file ngay trước khi sửa, chỉ sửa dòng P270); cập nhật docs/steps/TRANG-THAI.md; báo cáo theo Quy tắc chung mục 8.
```
