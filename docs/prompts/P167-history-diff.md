# P167 – FE: lịch sử phiên bản + diff mức từ

| Làn | Tính năng | Phụ thuộc |
|---|---|---|
| FE | F07 | [P165](./P165-editor-autosave.md) |

Dán nguyên khối dưới vào một cửa sổ Claude Code mới mở tại `E:\pm\WriteStoryApp`. Trạng thái của prompt được theo dõi trong [README.md](./README.md#tiến-độ).

```text
[P167] FE: lịch sử phiên bản + diff mức từ

Làm theo docs/prompts/README.md mục "Quy tắc chung".
Phụ thuộc phải xong trước: P165. Kiểm tra bảng Tiến độ trong docs/prompts/README.md; nếu chưa xong thì dừng và báo tôi.

Đọc trước:
- docs/steps/TRANG-THAI.md
- docs/implementation-plan.vi.md §24 (bảng quyết định)
- docs/features/F07-editor-va-phien-ban/fe.md
- docs/ui-design.vi.md §5.5

Việc cần làm:
1. `features/history/`: danh sách revision theo nguồn, diff theo đoạn rồi mức từ trong Web Worker (jsdiff + Intl.Segmenter('vi')), restore, UI xung đột 409.
2. Test (worker mock).

Phạm vi file: fe/src/features/history/
Xong khi: test pass.

Kết thúc: tick các mục đã làm trong checklist spec liên quan; đổi trạng thái P167 thành done trong bảng Tiến độ của docs/prompts/README.md (đọc lại file ngay trước khi sửa, chỉ sửa dòng P167); cập nhật docs/steps/TRANG-THAI.md; báo cáo theo Quy tắc chung mục 8.
```
