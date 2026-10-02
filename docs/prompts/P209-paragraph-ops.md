# P209 – AI: văn bản theo đoạn + ParagraphOps

| Làn | Tính năng | Phụ thuộc |
|---|---|---|
| AI | F09 / F10 | [P002](./P002-kiem-chung-ai-base.md) |

Dán nguyên khối dưới vào một cửa sổ Claude Code mới mở tại `E:\pm\WriteStoryApp`. Trạng thái của prompt được theo dõi trong [README.md](./README.md#tiến-độ).

```text
[P209] AI: văn bản theo đoạn + ParagraphOps

Làm theo docs/prompts/README.md mục "Quy tắc chung".
Phụ thuộc phải xong trước: P002. Kiểm tra bảng Tiến độ trong docs/prompts/README.md; nếu chưa xong thì dừng và báo tôi.

Đọc trước:
- docs/steps/TRANG-THAI.md
- docs/implementation-plan.vi.md §24 (bảng quyết định)
- docs/implementation-plan.vi.md §23.1.B
- docs/features/F10-viet-chuong-lien-mach/ai.md

Việc cần làm:
1. `contracts/paragraphs.py`: ParagraphText ([p:id] nội dung), ParagraphOps (replace/insert_after/delete).
2. Hàm render cho prompt và parse/validate ops (id tồn tại, không đụng đoạn ngoài phạm vi).
3. Test.

Phạm vi file: ai/src/writestory_ai/contracts/, ai/tests/
Xong khi: pytest ai pass.

Kết thúc: tick các mục đã làm trong checklist spec liên quan; đổi trạng thái P209 thành done trong bảng Tiến độ của docs/prompts/README.md (đọc lại file ngay trước khi sửa, chỉ sửa dòng P209); cập nhật docs/steps/TRANG-THAI.md; báo cáo theo Quy tắc chung mục 8.
```
