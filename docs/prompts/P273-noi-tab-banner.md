# P273 – FE: tab Nối + banner bị chặn

| Làn | Tính năng | Phụ thuộc |
|---|---|---|
| FE | F10 | [P272](./P272-ai-tab-stream.md) |

Dán nguyên khối dưới vào một cửa sổ Claude Code mới mở tại `E:\pm\WriteStoryApp`. Trạng thái của prompt được theo dõi trong [README.md](./README.md#tiến-độ).

```text
[P273] FE: tab Nối + banner bị chặn

Làm theo docs/prompts/README.md mục "Quy tắc chung".
Phụ thuộc phải xong trước: P272. Kiểm tra bảng Tiến độ trong docs/prompts/README.md; nếu chưa xong thì dừng và báo tôi.

Đọc trước:
- docs/steps/TRANG-THAI.md
- docs/implementation-plan.vi.md §24 (bảng quyết định)
- docs/features/F10-viet-chuong-lien-mach/fe.md
- docs/ui-design.vi.md §5.2, §24 D42

Việc cần làm:
1. Tab 'Nối': ending_state chương trước (sửa được), tail_text, kết quả seam, hook đến hạn.
2. Banner bị chặn/stale ở features/continuity, lắp vào workspace, các nút xử lý.
3. Test.

Phạm vi file: fe/src/features/continuity/
Xong khi: test pass.

Kết thúc: tick các mục đã làm trong checklist spec liên quan; đổi trạng thái P273 thành done trong bảng Tiến độ của docs/prompts/README.md (đọc lại file ngay trước khi sửa, chỉ sửa dòng P273); cập nhật docs/steps/TRANG-THAI.md; báo cáo theo Quy tắc chung mục 8.
```
