# P233 – BE: API trạng thái/bộ nhớ + ContextPort

| Làn | Tính năng | Phụ thuộc |
|---|---|---|
| BE | F09 | [P232](./P232-apply-delta-transaction.md), [P107](./P107-fts-tim-kiem.md) |

Dán nguyên khối dưới vào một cửa sổ Claude Code mới mở tại `E:\pm\WriteStoryApp`. Trạng thái của prompt được theo dõi trong [README.md](./README.md#tiến-độ).

```text
[P233] BE: API trạng thái/bộ nhớ + ContextPort

Làm theo docs/prompts/README.md mục "Quy tắc chung".
Phụ thuộc phải xong trước: P232, P107. Kiểm tra bảng Tiến độ trong docs/prompts/README.md; nếu chưa xong thì dừng và báo tôi.

Đọc trước:
- docs/steps/TRANG-THAI.md
- docs/implementation-plan.vi.md §24 (bảng quyết định)
- docs/features/F09-trang-thai-va-bo-nho/be.md
- docs/implementation-plan.vi.md §7 (API bổ sung)

Việc cần làm:
1. GET /v1/works/{id}/state?chapter=N, /state/changes, /summaries, PUT /v1/summaries/{id}, GET /v1/chapters/{id}/memory, /trace, GET /v1/works/{id}/search.
2. `infrastructure/ai/context_adapter.py` triển khai ContextPort cho composer (đọc DB, đóng transaction đọc trước khi gọi AI).
3. Index facts/hooks vào search; test.

Phạm vi file: be/src/writestory_be/modules/memory/, be/src/writestory_be/infrastructure/ai/, be/tests/
Xong khi: Test pass.

Kết thúc: tick các mục đã làm trong checklist spec liên quan; đổi trạng thái P233 thành done trong bảng Tiến độ của docs/prompts/README.md (đọc lại file ngay trước khi sửa, chỉ sửa dòng P233); cập nhật docs/steps/TRANG-THAI.md; báo cáo theo Quy tắc chung mục 8.
```
