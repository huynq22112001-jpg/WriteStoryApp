# P121 – AI: chính sách retry + ProviderLimiterPort

| Làn | Tính năng | Phụ thuộc |
|---|---|---|
| AI | F04 / F12 | [P118](./P118-adapter-anthropic.md) |

Dán nguyên khối dưới vào một cửa sổ Claude Code mới mở tại `E:\pm\WriteStoryApp`. Trạng thái của prompt được theo dõi trong [README.md](./README.md#tiến-độ).

```text
[P121] AI: chính sách retry + ProviderLimiterPort

Làm theo docs/prompts/README.md mục "Quy tắc chung".
Phụ thuộc phải xong trước: P118. Kiểm tra bảng Tiến độ trong docs/prompts/README.md; nếu chưa xong thì dừng và báo tôi.

Đọc trước:
- docs/steps/TRANG-THAI.md
- docs/implementation-plan.vi.md §24 (bảng quyết định)
- docs/features/F12-auto-write-da-truyen/ai.md
- docs/implementation-plan.vi.md §4.2, §24 D14

Việc cần làm:
1. `policies/retry.py`: phân loại lỗi, backoff + jitter, tối đa 3 lần, ưu tiên Retry-After, không retry 401/403/model-not-found.
2. `ports/limiter.py`: ProviderLimiterPort, Permit (BE triển khai ở P125).
3. Test với mock provider fail_sequence.

Phạm vi file: ai/src/writestory_ai/policies/, ai/src/writestory_ai/ports/, ai/tests/
Xong khi: pytest ai pass.

Kết thúc: tick các mục đã làm trong checklist spec liên quan; đổi trạng thái P121 thành done trong bảng Tiến độ của docs/prompts/README.md (đọc lại file ngay trước khi sửa, chỉ sửa dòng P121); cập nhật docs/steps/TRANG-THAI.md; báo cáo theo Quy tắc chung mục 8.
```
