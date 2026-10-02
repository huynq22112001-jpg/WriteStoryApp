# P116 – Style profile + ngôn ngữ + thể loại

| Làn | Tính năng | Phụ thuộc |
|---|---|---|
| BE | F05 | [P115](./P115-works-crud.md) |

Dán nguyên khối dưới vào một cửa sổ Claude Code mới mở tại `E:\pm\WriteStoryApp`. Trạng thái của prompt được theo dõi trong [README.md](./README.md#tiến-độ).

```text
[P116] Style profile + ngôn ngữ + thể loại

Làm theo docs/prompts/README.md mục "Quy tắc chung".
Phụ thuộc phải xong trước: P115. Kiểm tra bảng Tiến độ trong docs/prompts/README.md; nếu chưa xong thì dừng và báo tôi.

Đọc trước:
- docs/steps/TRANG-THAI.md
- docs/implementation-plan.vi.md §24 (bảng quyết định)
- docs/features/F05-thu-vien-va-tao-truyen/be.md
- docs/implementation-plan.vi.md §6.6, §24 D31

Việc cần làm:
1. Migration style_profile (tone_mark_style, vocab_register, dialogue_style, dialogue_dash_char, punctuation_rules, banned_phrases, voice_samples, revision).
2. GET /v1/languages, GET /v1/languages/{code}/genres đọc `ai/src/writestory_ai/languages/vi/genres.json` (bản tối giản – D31).
3. Test.

Phạm vi file: be/src/writestory_be/modules/works/, ai/src/writestory_ai/languages/vi/genres.json, be/migrations/versions/, be/tests/
Xong khi: Test pass.

Kết thúc: tick các mục đã làm trong checklist spec liên quan; đổi trạng thái P116 thành done trong bảng Tiến độ của docs/prompts/README.md (đọc lại file ngay trước khi sửa, chỉ sửa dòng P116); cập nhật docs/steps/TRANG-THAI.md; báo cáo theo Quy tắc chung mục 8.
```
