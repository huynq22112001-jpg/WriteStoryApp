# P115 – Bảng works + CRUD tác phẩm

| Làn | Tính năng | Phụ thuộc |
|---|---|---|
| BE | F05 | [P104](./P104-writer-queue-uow.md) |

Dán nguyên khối dưới vào một cửa sổ Claude Code mới mở tại `E:\pm\WriteStoryApp`. Trạng thái của prompt được theo dõi trong [README.md](./README.md#tiến-độ).

```text
[P115] Bảng works + CRUD tác phẩm

Làm theo docs/prompts/README.md mục "Quy tắc chung".
Phụ thuộc phải xong trước: P104. Kiểm tra bảng Tiến độ trong docs/prompts/README.md; nếu chưa xong thì dừng và báo tôi.

Đọc trước:
- docs/steps/TRANG-THAI.md
- docs/implementation-plan.vi.md §24 (bảng quyết định)
- docs/features/F05-thu-vien-va-tao-truyen/be.md
- docs/implementation-plan.vi.md §5 (works), §24 D6, D33

Việc cần làm:
1. Migration works (language, status, continuity_status, continuity_chapter_no, continuity_reason, target_chapters, chapter_length_min/max, wizard_step, revision, deleted_at…).
2. `modules/works/`: GET (cursor, lọc), POST, GET/{id}, PATCH (expected_revision), DELETE mềm, POST /{id}/open.
3. Test theo F05 be.md.

Phạm vi file: be/src/writestory_be/modules/works/, be/migrations/versions/, be/tests/
Xong khi: Test pass.

Kết thúc: tick các mục đã làm trong checklist spec liên quan; đổi trạng thái P115 thành done trong bảng Tiến độ của docs/prompts/README.md (đọc lại file ngay trước khi sửa, chỉ sửa dòng P115); cập nhật docs/steps/TRANG-THAI.md; báo cáo theo Quy tắc chung mục 8.
```
