# P215 – AI: bước Settle (delta + ending_state)

| Làn | Tính năng | Phụ thuộc |
|---|---|---|
| AI | F10 | [P214](./P214-writer-step.md), [P207](./P207-apply-delta-v01-v08.md) |

Dán nguyên khối dưới vào một cửa sổ Claude Code mới mở tại `E:\pm\WriteStoryApp`. Trạng thái của prompt được theo dõi trong [README.md](./README.md#tiến-độ).

```text
[P215] AI: bước Settle (delta + ending_state)

Làm theo docs/prompts/README.md mục "Quy tắc chung".
Phụ thuộc phải xong trước: P214, P207. Kiểm tra bảng Tiến độ trong docs/prompts/README.md; nếu chưa xong thì dừng và báo tôi.

Đọc trước:
- docs/steps/TRANG-THAI.md
- docs/implementation-plan.vi.md §24 (bảng quyết định)
- docs/features/F10-viet-chuong-lien-mach/ai.md (bước settle)
- docs/features/F09-trang-thai-va-bo-nho/ai.md

Việc cần làm:
1. Sinh StateDelta có evidence theo paragraph_id + EndingState (địa điểm, thời điểm, nhân vật có mặt, hành động dở dang, cảm xúc).
2. Structured output theo capabilities, fallback JSON + một lần sửa → STRUCTURED_OUTPUT_INVALID.
3. Test.

Phạm vi file: ai/src/writestory_ai/workflows/longform/settlement.py, ai/tests/
Xong khi: pytest ai pass.

Kết thúc: tick các mục đã làm trong checklist spec liên quan; đổi trạng thái P215 thành done trong bảng Tiến độ của docs/prompts/README.md (đọc lại file ngay trước khi sửa, chỉ sửa dòng P215); cập nhật docs/steps/TRANG-THAI.md; báo cáo theo Quy tắc chung mục 8.
```
