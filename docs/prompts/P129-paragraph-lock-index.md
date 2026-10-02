# P129 – BE: paragraph projection, khóa chương nền, index

| Làn | Tính năng | Phụ thuộc |
|---|---|---|
| BE | F07 | [P128](./P128-revision-diff-restore.md), [P107](./P107-fts-tim-kiem.md), [P105](./P105-work-locks.md) |

Dán nguyên khối dưới vào một cửa sổ Claude Code mới mở tại `E:\pm\WriteStoryApp`. Trạng thái của prompt được theo dõi trong [README.md](./README.md#tiến-độ).

```text
[P129] BE: paragraph projection, khóa chương nền, index

Làm theo docs/prompts/README.md mục "Quy tắc chung".
Phụ thuộc phải xong trước: P128, P107, P105. Kiểm tra bảng Tiến độ trong docs/prompts/README.md; nếu chưa xong thì dừng và báo tôi.

Đọc trước:
- docs/steps/TRANG-THAI.md
- docs/implementation-plan.vi.md §24 (bảng quyết định)
- docs/features/F07-editor-va-phien-ban/be.md
- docs/implementation-plan.vi.md §23.1.B, §23.2 #3, §24 D19

Việc cần làm:
1. `modules/chapters/paragraphs.py`: projection doc_json → đoạn có paragraph_id, new_paragraph_id, align_paragraphs.
2. EditLock: chương đang làm nền cho job viết → CHAPTER_READ_ONLY (423).
3. Index nội dung chương vào search (P107) khi tạo revision.
4. Test.

Phạm vi file: be/src/writestory_be/modules/chapters/, be/tests/
Xong khi: Test pass.

Kết thúc: tick các mục đã làm trong checklist spec liên quan; đổi trạng thái P129 thành done trong bảng Tiến độ của docs/prompts/README.md (đọc lại file ngay trước khi sửa, chỉ sửa dòng P129); cập nhật docs/steps/TRANG-THAI.md; báo cáo theo Quy tắc chung mục 8.
```
