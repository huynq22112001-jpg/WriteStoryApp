# P211 – AI: đếm token + cắt tail_text

| Làn | Tính năng | Phụ thuộc |
|---|---|---|
| AI | F09 | [P210](./P210-composer-context.md) |

Dán nguyên khối dưới vào một cửa sổ Claude Code mới mở tại `E:\pm\WriteStoryApp`. Trạng thái của prompt được theo dõi trong [README.md](./README.md#tiến-độ).

```text
[P211] AI: đếm token + cắt tail_text

Làm theo docs/prompts/README.md mục "Quy tắc chung".
Phụ thuộc phải xong trước: P210. Kiểm tra bảng Tiến độ trong docs/prompts/README.md; nếu chưa xong thì dừng và báo tôi.

Đọc trước:
- docs/steps/TRANG-THAI.md
- docs/implementation-plan.vi.md §24 (bảng quyết định)
- docs/features/F09-trang-thai-va-bo-nho/ai.md
- docs/implementation-plan.vi.md §23.3 #4

Việc cần làm:
1. Ước lượng token = âm tiết × tokens_per_syllable + biên 15%; hook gọi count_tokens của provider khi có.
2. tail_text 1.000–2.000 token cắt ở ranh giới đoạn.
3. Ngân sách theo max_input_tokens của model; test.

Phạm vi file: ai/src/writestory_ai/context/, ai/tests/
Xong khi: pytest ai pass.

Kết thúc: tick các mục đã làm trong checklist spec liên quan; đổi trạng thái P211 thành done trong bảng Tiến độ của docs/prompts/README.md (đọc lại file ngay trước khi sửa, chỉ sửa dòng P211); cập nhật docs/steps/TRANG-THAI.md; báo cáo theo Quy tắc chung mục 8.
```
