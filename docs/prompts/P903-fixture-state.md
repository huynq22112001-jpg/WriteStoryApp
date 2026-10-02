# P903 – TEST: StoryState mẫu + delta sai

| Làn | Tính năng | Phụ thuộc |
|---|---|---|
| TEST | tests | [P206](./P206-storystate-contracts.md) |

Dán nguyên khối dưới vào một cửa sổ Claude Code mới mở tại `E:\pm\WriteStoryApp`. Trạng thái của prompt được theo dõi trong [README.md](./README.md#tiến-độ).

```text
[P903] TEST: StoryState mẫu + delta sai

Làm theo docs/prompts/README.md mục "Quy tắc chung".
Phụ thuộc phải xong trước: P206. Kiểm tra bảng Tiến độ trong docs/prompts/README.md; nếu chưa xong thì dừng và báo tôi.

Đọc trước:
- docs/steps/TRANG-THAI.md
- docs/implementation-plan.vi.md §24 (bảng quyết định)
- docs/features/F09-trang-thai-va-bo-nho/ai.md (luật V01–V15)

Việc cần làm:
1. `tests/fixtures/state/`: StoryState theo chương cho tien_hiep_01; `invalid_deltas/` mỗi luật V01–V15 một ca sai kèm mã lỗi mong đợi.

Phạm vi file: tests/fixtures/state/
Xong khi: Fixture validate được với contracts P206.

Kết thúc: tick các mục đã làm trong checklist spec liên quan; đổi trạng thái P903 thành done trong bảng Tiến độ của docs/prompts/README.md (đọc lại file ngay trước khi sửa, chỉ sửa dòng P903); cập nhật docs/steps/TRANG-THAI.md; báo cáo theo Quy tắc chung mục 8.
```
