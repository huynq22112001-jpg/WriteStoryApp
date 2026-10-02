# P127 – BE: working copy autosave + quy tắc revision

| Làn | Tính năng | Phụ thuộc |
|---|---|---|
| BE | F07 | [P126](./P126-chapters-crud.md) |

Dán nguyên khối dưới vào một cửa sổ Claude Code mới mở tại `E:\pm\WriteStoryApp`. Trạng thái của prompt được theo dõi trong [README.md](./README.md#tiến-độ).

```text
[P127] BE: working copy autosave + quy tắc revision

Làm theo docs/prompts/README.md mục "Quy tắc chung".
Phụ thuộc phải xong trước: P126. Kiểm tra bảng Tiến độ trong docs/prompts/README.md; nếu chưa xong thì dừng và báo tôi.

Đọc trước:
- docs/steps/TRANG-THAI.md
- docs/implementation-plan.vi.md §24 (bảng quyết định)
- docs/features/F07-editor-va-phien-ban/be.md
- docs/implementation-plan.vi.md §23.2 #2, §24 D29

Việc cần làm:
1. Migration chapter_working_copy (base_revision_id, doc_json, content_hash, has_changes, client_session_id, client_seq).
2. GET/PUT /v1/chapters/{id}/working-copy (base revision), POST /snapshot, PUT /v1/chapters/{id} (tiêu đề/thay toàn văn, expected_revision).
3. Chuẩn hóa NFC qua gói ngôn ngữ; đếm âm tiết; quy tắc tạo revision (rời chương, nhàn 2 phút, trước/sau nhận AI, Ctrl+S, trước restore).
4. Test.

Phạm vi file: be/src/writestory_be/modules/chapters/, be/migrations/versions/, be/tests/
Xong khi: Test pass.

Kết thúc: tick các mục đã làm trong checklist spec liên quan; đổi trạng thái P127 thành done trong bảng Tiến độ của docs/prompts/README.md (đọc lại file ngay trước khi sửa, chỉ sửa dòng P127); cập nhật docs/steps/TRANG-THAI.md; báo cáo theo Quy tắc chung mục 8.
```
