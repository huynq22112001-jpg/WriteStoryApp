# P002 – Kiểm chứng code base AI

| Làn | Tính năng | Phụ thuộc |
|---|---|---|
| AI | S02 | [P001](./P001-cai-moi-truong-uv-python.md) |

Dán nguyên khối dưới vào một cửa sổ Claude Code mới mở tại `E:\pm\WriteStoryApp`. Trạng thái của prompt được theo dõi trong [README.md](./README.md#tiến-độ).

```text
[P002] Kiểm chứng code base AI

Làm theo docs/prompts/README.md mục "Quy tắc chung".
Phụ thuộc phải xong trước: P001. Kiểm tra bảng Tiến độ trong docs/prompts/README.md; nếu chưa xong thì dừng và báo tôi.

Đọc trước:
- docs/steps/TRANG-THAI.md
- docs/implementation-plan.vi.md §24 (bảng quyết định)
- docs/steps/TRANG-THAI.md
- docs/steps/S02-base-ai.md
- docs/features/F08-goi-ngon-ngu-vi/ai.md
- docs/features/F01-hop-dong-api-va-su-kien/ai.md

Việc cần làm:
1. `uv run pytest ai/tests -q` – sửa code/test cho pass, đúng spec (không nới lỏng assert sai spec).
2. `uv run ruff check ai` – sửa lỗi lint.
3. Xác nhận AI không import BE (test_boundaries).

Phạm vi file: ai/
Xong khi: pytest + ruff của ai/ pass.

Kết thúc: tick các mục đã làm trong checklist spec liên quan; đổi trạng thái P002 thành done trong bảng Tiến độ của docs/prompts/README.md (đọc lại file ngay trước khi sửa, chỉ sửa dòng P002); cập nhật docs/steps/TRANG-THAI.md; báo cáo theo Quy tắc chung mục 8.
```
