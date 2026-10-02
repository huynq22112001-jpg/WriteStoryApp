# P230 – BE: gói ngôn ngữ khi lưu + API kiểm tra

| Làn | Tính năng | Phụ thuộc |
|---|---|---|
| BE | F08 | [P129](./P129-paragraph-lock-index.md), [P204](./P204-kiem-tra-slop-chinh-ta.md) |

Dán nguyên khối dưới vào một cửa sổ Claude Code mới mở tại `E:\pm\WriteStoryApp`. Trạng thái của prompt được theo dõi trong [README.md](./README.md#tiến-độ).

```text
[P230] BE: gói ngôn ngữ khi lưu + API kiểm tra

Làm theo docs/prompts/README.md mục "Quy tắc chung".
Phụ thuộc phải xong trước: P129, P204. Kiểm tra bảng Tiến độ trong docs/prompts/README.md; nếu chưa xong thì dừng và báo tôi.

Đọc trước:
- docs/steps/TRANG-THAI.md
- docs/implementation-plan.vi.md §24 (bảng quyết định)
- docs/features/F08-goi-ngon-ngu-vi/be.md

Việc cần làm:
1. Chuẩn hóa văn bản khi lưu/paste qua LanguagePack của truyện.
2. GET/PUT /v1/languages/{code}/slop-list, POST /v1/languages/{code}/normalize, POST /v1/works/{id}/text/check, GET /v1/languages/{code}/genre-presets.
3. findings thêm check_id, confidence, message_key, params.
4. Test.

Phạm vi file: be/src/writestory_be/modules/language/, be/migrations/versions/, be/tests/
Xong khi: Test pass.

Kết thúc: tick các mục đã làm trong checklist spec liên quan; đổi trạng thái P230 thành done trong bảng Tiến độ của docs/prompts/README.md (đọc lại file ngay trước khi sửa, chỉ sửa dòng P230); cập nhật docs/steps/TRANG-THAI.md; báo cáo theo Quy tắc chung mục 8.
```
