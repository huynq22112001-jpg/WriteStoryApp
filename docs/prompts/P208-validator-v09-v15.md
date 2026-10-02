# P208 – AI: validator V09–V15

| Làn | Tính năng | Phụ thuộc |
|---|---|---|
| AI | F09 | [P207](./P207-apply-delta-v01-v08.md) |

Dán nguyên khối dưới vào một cửa sổ Claude Code mới mở tại `E:\pm\WriteStoryApp`. Trạng thái của prompt được theo dõi trong [README.md](./README.md#tiến-độ).

```text
[P208] AI: validator V09–V15

Làm theo docs/prompts/README.md mục "Quy tắc chung".
Phụ thuộc phải xong trước: P207. Kiểm tra bảng Tiến độ trong docs/prompts/README.md; nếu chưa xong thì dừng và báo tôi.

Đọc trước:
- docs/steps/TRANG-THAI.md
- docs/implementation-plan.vi.md §24 (bảng quyết định)
- docs/features/F09-trang-thai-va-bo-nho/ai.md

Việc cần làm:
1. V09–V15 (gồm hook quá hạn V14 → major, không chặn).
2. Test mỗi luật.

Phạm vi file: ai/src/writestory_ai/state/ (hoặc evaluators/), ai/tests/
Xong khi: pytest ai pass.

Kết thúc: tick các mục đã làm trong checklist spec liên quan; đổi trạng thái P208 thành done trong bảng Tiến độ của docs/prompts/README.md (đọc lại file ngay trước khi sửa, chỉ sửa dòng P208); cập nhật docs/steps/TRANG-THAI.md; báo cáo theo Quy tắc chung mục 8.
```
