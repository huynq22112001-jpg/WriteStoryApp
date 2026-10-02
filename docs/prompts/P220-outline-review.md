# P220 – AI: xét lại dàn ý mỗi K chương

| Làn | Tính năng | Phụ thuộc |
|---|---|---|
| AI | F10 | [P219](./P219-pipeline-orchestration.md) |

Dán nguyên khối dưới vào một cửa sổ Claude Code mới mở tại `E:\pm\WriteStoryApp`. Trạng thái của prompt được theo dõi trong [README.md](./README.md#tiến-độ).

```text
[P220] AI: xét lại dàn ý mỗi K chương

Làm theo docs/prompts/README.md mục "Quy tắc chung".
Phụ thuộc phải xong trước: P219. Kiểm tra bảng Tiến độ trong docs/prompts/README.md; nếu chưa xong thì dừng và báo tôi.

Đọc trước:
- docs/steps/TRANG-THAI.md
- docs/implementation-plan.vi.md §24 (bảng quyết định)
- docs/features/F10-viet-chuong-lien-mach/ai.md (outline_review)
- docs/implementation-plan.vi.md §23.3 #6

Việc cần làm:
1. OutlineProposal sửa story_events khi tới chương K hoặc ≥2 sự kiện moved; không đụng sự kiện locked.
2. Test.

Phạm vi file: ai/src/writestory_ai/workflows/longform/outline_review.py, ai/tests/
Xong khi: pytest ai pass.

Kết thúc: tick các mục đã làm trong checklist spec liên quan; đổi trạng thái P220 thành done trong bảng Tiến độ của docs/prompts/README.md (đọc lại file ngay trước khi sửa, chỉ sửa dòng P220); cập nhật docs/steps/TRANG-THAI.md; báo cáo theo Quy tắc chung mục 8.
```
