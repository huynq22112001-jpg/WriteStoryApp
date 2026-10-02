# P165 – FE: editor đầy đủ + autosave

| Làn | Tính năng | Phụ thuộc |
|---|---|---|
| FE | F07 | [P164](./P164-workspace-chapter-tree.md), [P015](./P015-paste-nfc-dem-am-tiet-ts.md) |

Dán nguyên khối dưới vào một cửa sổ Claude Code mới mở tại `E:\pm\WriteStoryApp`. Trạng thái của prompt được theo dõi trong [README.md](./README.md#tiến-độ).

```text
[P165] FE: editor đầy đủ + autosave

Làm theo docs/prompts/README.md mục "Quy tắc chung".
Phụ thuộc phải xong trước: P164, P015. Kiểm tra bảng Tiến độ trong docs/prompts/README.md; nếu chưa xong thì dừng và báo tôi.

Đọc trước:
- docs/steps/TRANG-THAI.md
- docs/implementation-plan.vi.md §24 (bảng quyết định)
- docs/features/F07-editor-va-phien-ban/fe.md
- docs/ui-design.vi.md §6

Việc cần làm:
1. ChapterEditor từ spike, bubble menu, drag handle, CharacterCount; `shouldRerenderOnTransaction: false`.
2. useAutosave debounce 500–1000 ms, flush khi rời chương/đóng cửa sổ, trạng thái lưu, Ctrl+S tạo snapshot.
3. Test.

Phạm vi file: fe/src/features/editor/
Xong khi: test pass.

Kết thúc: tick các mục đã làm trong checklist spec liên quan; đổi trạng thái P165 thành done trong bảng Tiến độ của docs/prompts/README.md (đọc lại file ngay trước khi sửa, chỉ sửa dòng P165); cập nhật docs/steps/TRANG-THAI.md; báo cáo theo Quy tắc chung mục 8.
```
