# P119 – AI: adapter OpenAI-compatible / Ollama

| Làn | Tính năng | Phụ thuộc |
|---|---|---|
| AI | F04 | [P002](./P002-kiem-chung-ai-base.md) |

Dán nguyên khối dưới vào một cửa sổ Claude Code mới mở tại `E:\pm\WriteStoryApp`. Trạng thái của prompt được theo dõi trong [README.md](./README.md#tiến-độ).

```text
[P119] AI: adapter OpenAI-compatible / Ollama

Làm theo docs/prompts/README.md mục "Quy tắc chung".
Phụ thuộc phải xong trước: P002. Kiểm tra bảng Tiến độ trong docs/prompts/README.md; nếu chưa xong thì dừng và báo tôi.

Đọc trước:
- docs/steps/TRANG-THAI.md
- docs/implementation-plan.vi.md §24 (bảng quyết định)
- docs/features/F04-cau-hinh-mo-hinh-ai/ai.md
- docs/implementation-plan.vi.md §7.1

Việc cần làm:
1. `providers/openai_compatible.py`: chat completions stream, usage nếu có (không có → reported=False), effort ánh xạ sang tham số reasoning khi model hỗ trợ, bỏ qua khi không.
2. Ollama/LM Studio dùng cùng adapter, không cần key.
3. Ánh xạ lỗi như P118; test bằng MockTransport.

Phạm vi file: ai/src/writestory_ai/providers/, ai/tests/
Xong khi: pytest ai pass.

Kết thúc: tick các mục đã làm trong checklist spec liên quan; đổi trạng thái P119 thành done trong bảng Tiến độ của docs/prompts/README.md (đọc lại file ngay trước khi sửa, chỉ sửa dòng P119); cập nhật docs/steps/TRANG-THAI.md; báo cáo theo Quy tắc chung mục 8.
```
