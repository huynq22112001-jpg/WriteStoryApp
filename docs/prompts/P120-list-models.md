# P120 – AI: liệt kê và chuẩn hóa model

| Làn | Tính năng | Phụ thuộc |
|---|---|---|
| AI | F04 | [P118](./P118-adapter-anthropic.md), [P119](./P119-adapter-openai-compatible.md) |

Dán nguyên khối dưới vào một cửa sổ Claude Code mới mở tại `E:\pm\WriteStoryApp`. Trạng thái của prompt được theo dõi trong [README.md](./README.md#tiến-độ).

```text
[P120] AI: liệt kê và chuẩn hóa model

Làm theo docs/prompts/README.md mục "Quy tắc chung".
Phụ thuộc phải xong trước: P118, P119. Kiểm tra bảng Tiến độ trong docs/prompts/README.md; nếu chưa xong thì dừng và báo tôi.

Đọc trước:
- docs/steps/TRANG-THAI.md
- docs/implementation-plan.vi.md §24 (bảng quyết định)
- docs/features/F04-cau-hinh-mo-hinh-ai/ai.md
- docs/implementation-plan.vi.md §7.1 (Lấy danh sách model)

Việc cần làm:
1. `contracts/models.py` ProviderModel (id, display_name, max_input_tokens, max_tokens, supported_efforts, capabilities).
2. list_models cho Anthropic (phân trang has_more/after_id, limit ≤ 1000, đọc capabilities.effort) và OpenAI-compatible (data[].id).
3. Test với response mẫu cả hai dạng.

Phạm vi file: ai/src/writestory_ai/providers/, ai/src/writestory_ai/contracts/, ai/tests/
Xong khi: pytest ai pass.

Kết thúc: tick các mục đã làm trong checklist spec liên quan; đổi trạng thái P120 thành done trong bảng Tiến độ của docs/prompts/README.md (đọc lại file ngay trước khi sửa, chỉ sửa dòng P120); cập nhật docs/steps/TRANG-THAI.md; báo cáo theo Quy tắc chung mục 8.
```
