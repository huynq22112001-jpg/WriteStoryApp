# P280 – FE: Story Bible – dàn ý, timeline, đồ thị, thanh trượt

| Làn | Tính năng | Phụ thuộc |
|---|---|---|
| FE | F06 | [P279](./P279-story-bible-characters.md) |

Dán nguyên khối dưới vào một cửa sổ Claude Code mới mở tại `E:\pm\WriteStoryApp`. Trạng thái của prompt được theo dõi trong [README.md](./README.md#tiến-độ).

```text
[P280] FE: Story Bible – dàn ý, timeline, đồ thị, thanh trượt

Làm theo docs/prompts/README.md mục "Quy tắc chung".
Phụ thuộc phải xong trước: P279. Kiểm tra bảng Tiến độ trong docs/prompts/README.md; nếu chưa xong thì dừng và báo tôi.

Đọc trước:
- docs/steps/TRANG-THAI.md
- docs/implementation-plan.vi.md §24 (bảng quyết định)
- docs/features/F06-nen-truyen-va-story-bible/fe.md
- docs/ui-design.vi.md §5.4

Việc cần làm:
1. Dàn ý sự kiện (trạng thái, locked), timeline lưới cột = chương, hàng = storyline, đồ thị quan hệ React Flow (lazy), thanh trượt chương xem StoryState.
2. Test.

Phạm vi file: fe/src/features/story_bible/
Xong khi: test pass.

Kết thúc: tick các mục đã làm trong checklist spec liên quan; đổi trạng thái P280 thành done trong bảng Tiến độ của docs/prompts/README.md (đọc lại file ngay trước khi sửa, chỉ sửa dòng P280); cập nhật docs/steps/TRANG-THAI.md; báo cáo theo Quy tắc chung mục 8.
```
