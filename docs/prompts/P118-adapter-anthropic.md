# P118 – AI: adapter Anthropic

| Làn | Tính năng | Phụ thuộc |
|---|---|---|
| AI | F04 | [P002](./P002-kiem-chung-ai-base.md) |

Dán nguyên khối dưới vào một cửa sổ Claude Code mới mở tại `E:\pm\WriteStoryApp`. Trạng thái của prompt được theo dõi trong [README.md](./README.md#tiến-độ).

```text
[P118] AI: adapter Anthropic

Làm theo docs/prompts/README.md mục "Quy tắc chung".
Phụ thuộc phải xong trước: P002. Kiểm tra bảng Tiến độ trong docs/prompts/README.md; nếu chưa xong thì dừng và báo tôi.

Đọc trước:
- docs/steps/TRANG-THAI.md
- docs/implementation-plan.vi.md §24 (bảng quyết định)
- docs/features/F04-cau-hinh-mo-hinh-ai/ai.md
- docs/implementation-plan.vi.md §7.1, §24 D14
- Tài liệu chính thức Anthropic Messages API (streaming, stop_reason, usage, output_config.effort) – đọc trước khi code

Việc cần làm:
1. `providers/anthropic.py` triển khai TextProvider: stream SSE, TextDelta/StreamDone, stop_reason refusal/max_tokens, usage gồm cache read/write, effort qua output_config.effort (chỉ gửi khi có).
2. Ánh xạ lỗi: 401/403 → ProviderAuthError, 429 + Retry-After → ProviderRateLimitError, 5xx → ProviderServerError, mất kết nối → ProviderUnreachableError.
3. Test bằng httpx.MockTransport với stream mẫu; không gọi API thật.

Phạm vi file: ai/src/writestory_ai/providers/, ai/tests/
Xong khi: pytest ai pass.

Kết thúc: tick các mục đã làm trong checklist spec liên quan; đổi trạng thái P118 thành done trong bảng Tiến độ của docs/prompts/README.md (đọc lại file ngay trước khi sửa, chỉ sửa dòng P118); cập nhật docs/steps/TRANG-THAI.md; báo cáo theo Quy tắc chung mục 8.
```
