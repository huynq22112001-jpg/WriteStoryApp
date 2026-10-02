# P122 – BE: CRUD provider

| Làn | Tính năng | Phụ thuộc |
|---|---|---|
| BE | F04 | [P113](./P113-vault-api.md) |

Dán nguyên khối dưới vào một cửa sổ Claude Code mới mở tại `E:\pm\WriteStoryApp`. Trạng thái của prompt được theo dõi trong [README.md](./README.md#tiến-độ).

```text
[P122] BE: CRUD provider

Làm theo docs/prompts/README.md mục "Quy tắc chung".
Phụ thuộc phải xong trước: P113. Kiểm tra bảng Tiến độ trong docs/prompts/README.md; nếu chưa xong thì dừng và báo tôi.

Đọc trước:
- docs/steps/TRANG-THAI.md
- docs/implementation-plan.vi.md §24 (bảng quyết định)
- docs/features/F04-cau-hinh-mo-hinh-ai/be.md
- docs/implementation-plan.vi.md §5 (providers), §24 D27

Việc cần làm:
1. Migration providers (name, protocol, base_url, secret_ref, auto_discover, prefer_long_context, default_effort, enabled, trạng thái discovery/kết nối, revision).
2. POST/GET/PATCH/DELETE /v1/providers; key ghi qua SecretStore; POST /v1/providers/test.
3. Test.

Phạm vi file: be/src/writestory_be/modules/providers/, be/migrations/versions/, be/tests/
Xong khi: Test pass.

Kết thúc: tick các mục đã làm trong checklist spec liên quan; đổi trạng thái P122 thành done trong bảng Tiến độ của docs/prompts/README.md (đọc lại file ngay trước khi sửa, chỉ sửa dòng P122); cập nhật docs/steps/TRANG-THAI.md; báo cáo theo Quy tắc chung mục 8.
```
