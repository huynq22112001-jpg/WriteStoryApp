# P128 – BE: diff, restore, xung đột 409

| Làn | Tính năng | Phụ thuộc |
|---|---|---|
| BE | F07 | [P127](./P127-working-copy-revision.md) |

Dán nguyên khối dưới vào một cửa sổ Claude Code mới mở tại `E:\pm\WriteStoryApp`. Trạng thái của prompt được theo dõi trong [README.md](./README.md#tiến-độ).

```text
[P128] BE: diff, restore, xung đột 409

Làm theo docs/prompts/README.md mục "Quy tắc chung".
Phụ thuộc phải xong trước: P127. Kiểm tra bảng Tiến độ trong docs/prompts/README.md; nếu chưa xong thì dừng và báo tôi.

Đọc trước:
- docs/steps/TRANG-THAI.md
- docs/implementation-plan.vi.md §24 (bảng quyết định)
- docs/features/F07-editor-va-phien-ban/be.md
- docs/features/F01-hop-dong-api-va-su-kien/be.md (REVISION_CONFLICT)

Việc cần làm:
1. GET /v1/chapters/{id}/revisions, /revisions/{rev}, /revisions/{a}/diff/{b} (b có thể là `working`) – diff theo paragraph_id.
2. POST /revisions/{rev}/restore tạo revision mới.
3. expected_revision lệch → 409 kèm bản hiện tại để FE dựng diff.
4. Test.

Phạm vi file: be/src/writestory_be/modules/chapters/, be/tests/
Xong khi: Test pass.

Kết thúc: tick các mục đã làm trong checklist spec liên quan; đổi trạng thái P128 thành done trong bảng Tiến độ của docs/prompts/README.md (đọc lại file ngay trước khi sửa, chỉ sửa dòng P128); cập nhật docs/steps/TRANG-THAI.md; báo cáo theo Quy tắc chung mục 8.
```
