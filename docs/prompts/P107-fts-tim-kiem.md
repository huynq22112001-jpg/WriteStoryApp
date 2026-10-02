# P107 – Hạ tầng tìm kiếm FTS5 tiếng Việt

| Làn | Tính năng | Phụ thuộc |
|---|---|---|
| BE | F02 | [P102](./P102-migration-baseline.md) |

Dán nguyên khối dưới vào một cửa sổ Claude Code mới mở tại `E:\pm\WriteStoryApp`. Trạng thái của prompt được theo dõi trong [README.md](./README.md#tiến-độ).

```text
[P107] Hạ tầng tìm kiếm FTS5 tiếng Việt

Làm theo docs/prompts/README.md mục "Quy tắc chung".
Phụ thuộc phải xong trước: P102. Kiểm tra bảng Tiến độ trong docs/prompts/README.md; nếu chưa xong thì dừng và báo tôi.

Đọc trước:
- docs/steps/TRANG-THAI.md
- docs/implementation-plan.vi.md §24 (bảng quyết định)
- docs/features/F02-nen-du-lieu/be.md (search_documents, search_fts, search_trigram)
- docs/implementation-plan.vi.md §5, §24 D25
- T13 (ca FTS)

Việc cần làm:
1. Migration `0003_f02_search`: search_documents + FTS5 `unicode61 remove_diacritics 2` trên cột đã fold + bảng trigram.
2. normalize_for_search dùng LanguagePack.search_fold của package AI cho cả nội dung và câu truy vấn.
3. register_search_indexer, index/xóa/tìm, bm25, trả nguồn (loại, id, đoạn).
4. Test: 'nguyen'→'Nguyễn', 'oc'→'Ộc', 'duong'→'Đường' đều khớp.

Phạm vi file: be/src/writestory_be/infrastructure/db/, be/migrations/versions/, be/tests/
Xong khi: Test pass.

Kết thúc: tick các mục đã làm trong checklist spec liên quan; đổi trạng thái P107 thành done trong bảng Tiến độ của docs/prompts/README.md (đọc lại file ngay trước khi sửa, chỉ sửa dòng P107); cập nhật docs/steps/TRANG-THAI.md; báo cáo theo Quy tắc chung mục 8.
```
