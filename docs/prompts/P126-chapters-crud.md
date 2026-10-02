# P126 – BE: bảng chương + tạo/xóa/sắp xếp

| Làn | Tính năng | Phụ thuộc |
|---|---|---|
| BE | F07 | [P115](./P115-works-crud.md) |

Dán nguyên khối dưới vào một cửa sổ Claude Code mới mở tại `E:\pm\WriteStoryApp`. Trạng thái của prompt được theo dõi trong [README.md](./README.md#tiến-độ).

```text
[P126] BE: bảng chương + tạo/xóa/sắp xếp

Làm theo docs/prompts/README.md mục "Quy tắc chung".
Phụ thuộc phải xong trước: P115. Kiểm tra bảng Tiến độ trong docs/prompts/README.md; nếu chưa xong thì dừng và báo tôi.

Đọc trước:
- docs/steps/TRANG-THAI.md
- docs/implementation-plan.vi.md §24 (bảng quyết định)
- docs/features/F07-editor-va-phien-ban/be.md
- docs/implementation-plan.vi.md §5 (chapters), §23.2 #4

Việc cần làm:
1. Migration chapters (status, state_applied, revision_count, syllable_count, char_count, deleted_at), chapter_revisions (revision_no, parent, source manual|auto_snapshot|agent|revise|restore|import, doc_json, paragraphs_json, content_hash…).
2. POST /v1/works/{id}/chapters, DELETE /v1/chapters/{id}, POST /v1/works/{id}/chapters/reorder; khi truyện đang chạy → CHAPTER_RANGE_CONFLICT.
3. Test.

Phạm vi file: be/src/writestory_be/modules/chapters/, be/migrations/versions/, be/tests/
Xong khi: Test pass.

Kết thúc: tick các mục đã làm trong checklist spec liên quan; đổi trạng thái P126 thành done trong bảng Tiến độ của docs/prompts/README.md (đọc lại file ngay trước khi sửa, chỉ sửa dòng P126); cập nhật docs/steps/TRANG-THAI.md; báo cáo theo Quy tắc chung mục 8.
```
