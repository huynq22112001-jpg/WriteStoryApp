# P125 – BE: limiter theo provider

| Làn | Tính năng | Phụ thuộc |
|---|---|---|
| BE | F04 / F12 | [P121](./P121-retry-limiter-port.md), [P122](./P122-providers-crud.md) |

Dán nguyên khối dưới vào một cửa sổ Claude Code mới mở tại `E:\pm\WriteStoryApp`. Trạng thái của prompt được theo dõi trong [README.md](./README.md#tiến-độ).

```text
[P125] BE: limiter theo provider

Làm theo docs/prompts/README.md mục "Quy tắc chung".
Phụ thuộc phải xong trước: P121, P122. Kiểm tra bảng Tiến độ trong docs/prompts/README.md; nếu chưa xong thì dừng và báo tôi.

Đọc trước:
- docs/steps/TRANG-THAI.md
- docs/implementation-plan.vi.md §24 (bảng quyết định)
- docs/features/F12-auto-write-da-truyen/be.md
- docs/implementation-plan.vi.md §4.2, §24 D14

Việc cần làm:
1. Migration provider_limits (max_concurrent_requests, rpm, tpm, max_retries, cooldown_until…).
2. `infrastructure/ai/limits.py` triển khai ProviderLimiterPort: semaphore, token bucket RPM/TPM, cooldown chung theo Retry-After.
3. GET/PUT /v1/providers/{id}/limits.
4. Test: không vượt concurrency; 429 làm cả provider chờ đúng Retry-After.

Phạm vi file: be/src/writestory_be/infrastructure/ai/, be/src/writestory_be/modules/providers/, be/migrations/versions/, be/tests/
Xong khi: Test pass.

Kết thúc: tick các mục đã làm trong checklist spec liên quan; đổi trạng thái P125 thành done trong bảng Tiến độ của docs/prompts/README.md (đọc lại file ngay trước khi sửa, chỉ sửa dòng P125); cập nhật docs/steps/TRANG-THAI.md; báo cáo theo Quy tắc chung mục 8.
```
