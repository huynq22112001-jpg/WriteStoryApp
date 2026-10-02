# P216 – AI: validator LLM + kiểm tra mối nối

| Làn | Tính năng | Phụ thuộc |
|---|---|---|
| AI | F10 | [P215](./P215-settlement-step.md) |

Dán nguyên khối dưới vào một cửa sổ Claude Code mới mở tại `E:\pm\WriteStoryApp`. Trạng thái của prompt được theo dõi trong [README.md](./README.md#tiến-độ).

```text
[P216] AI: validator LLM + kiểm tra mối nối

Làm theo docs/prompts/README.md mục "Quy tắc chung".
Phụ thuộc phải xong trước: P215. Kiểm tra bảng Tiến độ trong docs/prompts/README.md; nếu chưa xong thì dừng và báo tôi.

Đọc trước:
- docs/steps/TRANG-THAI.md
- docs/implementation-plan.vi.md §24 (bảng quyết định)
- docs/features/F10-viet-chuong-lien-mach/ai.md (validate, seam)
- docs/implementation-plan.vi.md §6.2 bước 7–8

Việc cần làm:
1. Validate: xác định (P207/P208) trước, LLM sau có trích dẫn.
2. seam_check: đoạn mở chương N so với ending_state(N-1) (địa điểm, thời điểm, ai có mặt, cảm xúc, hành động dở dang) → SeamResult.
3. Test với scripted outputs: seam pass / fail.

Phạm vi file: ai/src/writestory_ai/workflows/longform/validator.py, seam_check.py, ai/tests/
Xong khi: pytest ai pass.

Kết thúc: tick các mục đã làm trong checklist spec liên quan; đổi trạng thái P216 thành done trong bảng Tiến độ của docs/prompts/README.md (đọc lại file ngay trước khi sửa, chỉ sửa dòng P216); cập nhật docs/steps/TRANG-THAI.md; báo cáo theo Quy tắc chung mục 8.
```
