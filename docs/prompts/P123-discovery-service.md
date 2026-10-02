# P123 – BE: tự lấy danh sách model + merge

| Làn | Tính năng | Phụ thuộc |
|---|---|---|
| BE | F04 | [P122](./P122-providers-crud.md), [P120](./P120-list-models.md) |

Dán nguyên khối dưới vào một cửa sổ Claude Code mới mở tại `E:\pm\WriteStoryApp`. Trạng thái của prompt được theo dõi trong [README.md](./README.md#tiến-độ).

```text
[P123] BE: tự lấy danh sách model + merge

Làm theo docs/prompts/README.md mục "Quy tắc chung".
Phụ thuộc phải xong trước: P122, P120. Kiểm tra bảng Tiến độ trong docs/prompts/README.md; nếu chưa xong thì dừng và báo tôi.

Đọc trước:
- docs/steps/TRANG-THAI.md
- docs/implementation-plan.vi.md §24 (bảng quyết định)
- docs/features/F04-cau-hinh-mo-hinh-ai/be.md
- docs/implementation-plan.vi.md §7.1
- docs/tests/flows/T03-cau-hinh-mo-hinh-ai.md

Việc cần làm:
1. Migration provider_models (position, source, user_edited_fields, missing_since, giá/1M token, allowed_roles, tokens_per_syllable…).
2. `infrastructure/ai/discovery.py`: gọi adapter list_models; merge không ghi đè trường người dùng sửa; đánh dấu model biến mất; lưu lỗi.
3. POST /v1/providers/{id}/discover; chạy nền khi khởi động nếu bật.
4. Test kịch bản T03 phần BE.

Phạm vi file: be/src/writestory_be/modules/providers/, be/src/writestory_be/infrastructure/ai/, be/migrations/versions/, be/tests/
Xong khi: Test pass.

Kết thúc: tick các mục đã làm trong checklist spec liên quan; đổi trạng thái P123 thành done trong bảng Tiến độ của docs/prompts/README.md (đọc lại file ngay trước khi sửa, chỉ sửa dòng P123); cập nhật docs/steps/TRANG-THAI.md; báo cáo theo Quy tắc chung mục 8.
```
