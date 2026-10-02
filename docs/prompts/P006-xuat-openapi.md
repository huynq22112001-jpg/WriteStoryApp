# P006 – Xuất OpenAPI có ErrorResponse + EventEnvelope

| Làn | Tính năng | Phụ thuộc |
|---|---|---|
| BE | F01 / S05 | [P003](./P003-kiem-chung-be-base.md) |

Dán nguyên khối dưới vào một cửa sổ Claude Code mới mở tại `E:\pm\WriteStoryApp`. Trạng thái của prompt được theo dõi trong [README.md](./README.md#tiến-độ).

```text
[P006] Xuất OpenAPI có ErrorResponse + EventEnvelope

Làm theo docs/prompts/README.md mục "Quy tắc chung".
Phụ thuộc phải xong trước: P003. Kiểm tra bảng Tiến độ trong docs/prompts/README.md; nếu chưa xong thì dừng và báo tôi.

Đọc trước:
- docs/steps/TRANG-THAI.md
- docs/implementation-plan.vi.md §24 (bảng quyết định)
- docs/steps/S05-hop-dong-openapi.md
- docs/features/F01-hop-dong-api-va-su-kien/be.md

Việc cần làm:
1. Tạo `be/src/writestory_be/api/openapi.py`: chèn `EventEnvelope` và `ErrorResponse` vào `components.schemas` (TypeAdapter json_schema, ref_template), gắn vào `create_app`.
2. Chạy `uv run python tools/contracts/export_openapi.py` → `contracts/openapi.json`.
3. Test `be/tests/contract/test_openapi_snapshot.py`: mọi route có response default ErrorResponse; EventEnvelope có trong components.

Phạm vi file: be/src/writestory_be/api/openapi.py, be/src/writestory_be/main.py, contracts/, be/tests/contract/
Xong khi: Test contract pass; chạy export 2 lần không đổi file.

Kết thúc: tick các mục đã làm trong checklist spec liên quan; đổi trạng thái P006 thành done trong bảng Tiến độ của docs/prompts/README.md (đọc lại file ngay trước khi sửa, chỉ sửa dòng P006); cập nhật docs/steps/TRANG-THAI.md; báo cáo theo Quy tắc chung mục 8.
```
