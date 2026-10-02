# P221 – AI: workflow sửa theo yêu cầu tác giả

| Làn | Tính năng | Phụ thuộc |
|---|---|---|
| AI | F11 | [P219](./P219-pipeline-orchestration.md) |

Dán nguyên khối dưới vào một cửa sổ Claude Code mới mở tại `E:\pm\WriteStoryApp`. Trạng thái của prompt được theo dõi trong [README.md](./README.md#tiến-độ).

```text
[P221] AI: workflow sửa theo yêu cầu tác giả

Làm theo docs/prompts/README.md mục "Quy tắc chung".
Phụ thuộc phải xong trước: P219. Kiểm tra bảng Tiến độ trong docs/prompts/README.md; nếu chưa xong thì dừng và báo tôi.

Đọc trước:
- docs/steps/TRANG-THAI.md
- docs/implementation-plan.vi.md §24 (bảng quyết định)
- docs/features/F11-candidate-review-va-sua/ai.md

Việc cần làm:
1. Revise theo phạm vi (đoạn chọn / nhiều đoạn / cả chương), mode spot_fix|polish|rewrite|rework, trả ParagraphOps + đề xuất resettle.
2. Test.

Phạm vi file: ai/src/writestory_ai/workflows/longform/revise.py, ai/tests/
Xong khi: pytest ai pass.

Kết thúc: tick các mục đã làm trong checklist spec liên quan; đổi trạng thái P221 thành done trong bảng Tiến độ của docs/prompts/README.md (đọc lại file ngay trước khi sửa, chỉ sửa dòng P221); cập nhật docs/steps/TRANG-THAI.md; báo cáo theo Quy tắc chung mục 8.
```
