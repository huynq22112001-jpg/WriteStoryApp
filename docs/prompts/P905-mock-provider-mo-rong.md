# P905 – TEST: mở rộng mock provider

| Làn | Tính năng | Phụ thuộc |
|---|---|---|
| TEST | tests | [P002](./P002-kiem-chung-ai-base.md) |

Dán nguyên khối dưới vào một cửa sổ Claude Code mới mở tại `E:\pm\WriteStoryApp`. Trạng thái của prompt được theo dõi trong [README.md](./README.md#tiến-độ).

```text
[P905] TEST: mở rộng mock provider

Làm theo docs/prompts/README.md mục "Quy tắc chung".
Phụ thuộc phải xong trước: P002. Kiểm tra bảng Tiến độ trong docs/prompts/README.md; nếu chưa xong thì dừng và báo tôi.

Đọc trước:
- docs/steps/TRANG-THAI.md
- docs/implementation-plan.vi.md §24 (bảng quyết định)
- docs/tests/README.md (Mock provider)

Việc cần làm:
1. `ai/src/writestory_ai/providers/mock.py`: scripted_outputs theo bước, bad_json_on, models_endpoint (dạng Anthropic/OpenAI, models_pages), require_key, usage giả, tốc độ token.
2. Test cho từng tham số mới.

Phạm vi file: ai/src/writestory_ai/providers/mock.py, ai/tests/
Xong khi: pytest ai pass.

Kết thúc: tick các mục đã làm trong checklist spec liên quan; đổi trạng thái P905 thành done trong bảng Tiến độ của docs/prompts/README.md (đọc lại file ngay trước khi sửa, chỉ sửa dòng P905); cập nhật docs/steps/TRANG-THAI.md; báo cáo theo Quy tắc chung mục 8.
```
