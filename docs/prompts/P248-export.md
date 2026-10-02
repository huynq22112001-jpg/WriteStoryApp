# P248 – BE: xuất TXT/Markdown/EPUB

| Làn | Tính năng | Phụ thuộc |
|---|---|---|
| BE | F13 | [P129](./P129-paragraph-lock-index.md) |

Dán nguyên khối dưới vào một cửa sổ Claude Code mới mở tại `E:\pm\WriteStoryApp`. Trạng thái của prompt được theo dõi trong [README.md](./README.md#tiến-độ).

```text
[P248] BE: xuất TXT/Markdown/EPUB

Làm theo docs/prompts/README.md mục "Quy tắc chung".
Phụ thuộc phải xong trước: P129. Kiểm tra bảng Tiến độ trong docs/prompts/README.md; nếu chưa xong thì dừng và báo tôi.

Đọc trước:
- docs/steps/TRANG-THAI.md
- docs/implementation-plan.vi.md §24 (bảng quyết định)
- docs/features/F13-xuat-va-sao-luu/be.md
- docs/tests/flows/T16-xuat-va-sao-luu.md

Việc cần làm:
1. POST /v1/exports (job), GET /v1/works/{id}/exports, GET/DELETE /v1/exports/{id}; khoảng chương, metadata, NFC, file tạm + rename vào data/exports/<work-id>/, export_receipts có source revision/hash.
2. Test.

Phạm vi file: be/src/writestory_be/modules/operations/export*, be/migrations/versions/, be/tests/
Xong khi: Test pass.

Kết thúc: tick các mục đã làm trong checklist spec liên quan; đổi trạng thái P248 thành done trong bảng Tiến độ của docs/prompts/README.md (đọc lại file ngay trước khi sửa, chỉ sửa dòng P248); cập nhật docs/steps/TRANG-THAI.md; báo cáo theo Quy tắc chung mục 8.
```
