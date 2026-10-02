# P003 – Kiểm chứng code base BE

| Làn | Tính năng | Phụ thuộc |
|---|---|---|
| BE | S03 | [P001](./P001-cai-moi-truong-uv-python.md) |

Dán nguyên khối dưới vào một cửa sổ Claude Code mới mở tại `E:\pm\WriteStoryApp`. Trạng thái của prompt được theo dõi trong [README.md](./README.md#tiến-độ).

```text
[P003] Kiểm chứng code base BE

Làm theo docs/prompts/README.md mục "Quy tắc chung".
Phụ thuộc phải xong trước: P001. Kiểm tra bảng Tiến độ trong docs/prompts/README.md; nếu chưa xong thì dừng và báo tôi.

Đọc trước:
- docs/steps/TRANG-THAI.md
- docs/implementation-plan.vi.md §24 (bảng quyết định)
- docs/steps/TRANG-THAI.md
- docs/steps/S03-base-be.md
- docs/features/F00-nen-tang-desktop/be.md
- docs/features/F01-hop-dong-api-va-su-kien/be.md

Việc cần làm:
1. `uv run pytest be/tests -q` – sửa cho pass, đúng spec F00/F01.
2. `uv run ruff check be tools`.
3. Thêm mã `PROVIDER_SERVER_ERROR` (HTTP 502, retryable) vào `be/src/writestory_be/core/errors.py` (mock provider đã dùng); ghi vào 'Tên mới đề xuất' của F01 be.md.

Phạm vi file: be/, tools/
Xong khi: pytest + ruff của be/ pass.

Kết thúc: tick các mục đã làm trong checklist spec liên quan; đổi trạng thái P003 thành done trong bảng Tiến độ của docs/prompts/README.md (đọc lại file ngay trước khi sửa, chỉ sửa dòng P003); cập nhật docs/steps/TRANG-THAI.md; báo cáo theo Quy tắc chung mục 8.
```
