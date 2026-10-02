# P222 – AI: workflow nền truyện

| Làn | Tính năng | Phụ thuộc |
|---|---|---|
| AI | F06 | [P206](./P206-storystate-contracts.md), [P205](./P205-prompt-loader.md) |

Dán nguyên khối dưới vào một cửa sổ Claude Code mới mở tại `E:\pm\WriteStoryApp`. Trạng thái của prompt được theo dõi trong [README.md](./README.md#tiến-độ).

```text
[P222] AI: workflow nền truyện

Làm theo docs/prompts/README.md mục "Quy tắc chung".
Phụ thuộc phải xong trước: P206, P205. Kiểm tra bảng Tiến độ trong docs/prompts/README.md; nếu chưa xong thì dừng và báo tôi.

Đọc trước:
- docs/steps/TRANG-THAI.md
- docs/implementation-plan.vi.md §24 (bảng quyết định)
- docs/features/F06-nen-truyen-va-story-bible/ai.md
- docs/implementation-plan.vi.md §6.1, FL03

Việc cần làm:
1. 3 giai đoạn có checkpoint: story frame + quy tắc; nhân vật + bí danh + quan hệ + quy tắc xưng hô; dàn ý sự kiện có phụ thuộc + chương dự kiến + hook due_by_chapter.
2. Seed StoryState chương 0.
3. Test với mock.

Phạm vi file: ai/src/writestory_ai/workflows/longform/foundation.py, contracts/foundation.py, languages/vi/prompts/foundation/, ai/tests/
Xong khi: pytest ai pass.

Kết thúc: tick các mục đã làm trong checklist spec liên quan; đổi trạng thái P222 thành done trong bảng Tiến độ của docs/prompts/README.md (đọc lại file ngay trước khi sửa, chỉ sửa dòng P222); cập nhật docs/steps/TRANG-THAI.md; báo cáo theo Quy tắc chung mục 8.
```
