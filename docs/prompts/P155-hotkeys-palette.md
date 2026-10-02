# P155 – FE: phím tắt + command palette

| Làn | Tính năng | Phụ thuộc |
|---|---|---|
| FE | UI | [P152](./P152-app-shell.md) |

Dán nguyên khối dưới vào một cửa sổ Claude Code mới mở tại `E:\pm\WriteStoryApp`. Trạng thái của prompt được theo dõi trong [README.md](./README.md#tiến-độ).

```text
[P155] FE: phím tắt + command palette

Làm theo docs/prompts/README.md mục "Quy tắc chung".
Phụ thuộc phải xong trước: P152. Kiểm tra bảng Tiến độ trong docs/prompts/README.md; nếu chưa xong thì dừng và báo tôi.

Đọc trước:
- docs/steps/TRANG-THAI.md
- docs/implementation-plan.vi.md §24 (bảng quyết định)
- docs/ui-design.vi.md §8

Việc cần làm:
1. react-hotkeys-hook: Ctrl+K (palette cmdk), Ctrl+B / Ctrl+Alt+B (panel), Ctrl+Shift+W (Phòng viết).
2. Palette điều hướng tới các trang hiện có.
3. Test.

Phạm vi file: fe/src/app/, fe/src/shared/
Xong khi: test pass.

Kết thúc: tick các mục đã làm trong checklist spec liên quan; đổi trạng thái P155 thành done trong bảng Tiến độ của docs/prompts/README.md (đọc lại file ngay trước khi sửa, chỉ sửa dòng P155); cập nhật docs/steps/TRANG-THAI.md; báo cáo theo Quy tắc chung mục 8.
```
