# P239 – BE: findings resolve/dismiss

| Làn | Tính năng | Phụ thuộc |
|---|---|---|
| BE | F11 | [P238](./P238-candidate-accept.md) |

Dán nguyên khối dưới vào một cửa sổ Claude Code mới mở tại `E:\pm\WriteStoryApp`. Trạng thái của prompt được theo dõi trong [README.md](./README.md#tiến-độ).

```text
[P239] BE: findings resolve/dismiss

Làm theo docs/prompts/README.md mục "Quy tắc chung".
Phụ thuộc phải xong trước: P238. Kiểm tra bảng Tiến độ trong docs/prompts/README.md; nếu chưa xong thì dừng và báo tôi.

Đọc trước:
- docs/steps/TRANG-THAI.md
- docs/implementation-plan.vi.md §24 (bảng quyết định)
- docs/features/F11-candidate-review-va-sua/be.md
- docs/implementation-plan.vi.md §24 D39

Việc cần làm:
1. GET /v1/works/{id}/findings, POST /v1/findings/{id}/resolve | dismiss; ghi chú chỉ bỏ qua finding từ LLM, không bỏ qua validator xác định/schema.
2. Event finding.added/updated; test.

Phạm vi file: be/src/writestory_be/modules/longform/, be/tests/
Xong khi: Test pass.

Kết thúc: tick các mục đã làm trong checklist spec liên quan; đổi trạng thái P239 thành done trong bảng Tiến độ của docs/prompts/README.md (đọc lại file ngay trước khi sửa, chỉ sửa dòng P239); cập nhật docs/steps/TRANG-THAI.md; báo cáo theo Quy tắc chung mục 8.
```
