# P212 – AI: tóm tắt phân tầng

| Làn | Tính năng | Phụ thuộc |
|---|---|---|
| AI | F09 | [P210](./P210-composer-context.md), [P205](./P205-prompt-loader.md) |

Dán nguyên khối dưới vào một cửa sổ Claude Code mới mở tại `E:\pm\WriteStoryApp`. Trạng thái của prompt được theo dõi trong [README.md](./README.md#tiến-độ).

```text
[P212] AI: tóm tắt phân tầng

Làm theo docs/prompts/README.md mục "Quy tắc chung".
Phụ thuộc phải xong trước: P210, P205. Kiểm tra bảng Tiến độ trong docs/prompts/README.md; nếu chưa xong thì dừng và báo tôi.

Đọc trước:
- docs/steps/TRANG-THAI.md
- docs/implementation-plan.vi.md §24 (bảng quyết định)
- docs/features/F09-trang-thai-va-bo-nho/ai.md
- docs/implementation-plan.vi.md §23.3 #1
- docs/tests/flows/T14-truyen-dai-va-ngu-canh.md

Việc cần làm:
1. Schema tóm tắt chương / arc / synopsis; bước summarize_chapter và summarize_hierarchy (mỗi arc hoặc 10–20 chương) với prompt tiếng Việt.
2. Composer dùng synopsis + arc hiện tại + K tóm tắt gần nhất.
3. Test với mock provider: truyện 220 chương giữ context trong ngân sách.

Phạm vi file: ai/src/writestory_ai/workflows/longform/summaries.py, context/, languages/vi/prompts/, ai/tests/
Xong khi: pytest ai pass.

Kết thúc: tick các mục đã làm trong checklist spec liên quan; đổi trạng thái P212 thành done trong bảng Tiến độ của docs/prompts/README.md (đọc lại file ngay trước khi sửa, chỉ sửa dòng P212); cập nhật docs/steps/TRANG-THAI.md; báo cáo theo Quy tắc chung mục 8.
```
