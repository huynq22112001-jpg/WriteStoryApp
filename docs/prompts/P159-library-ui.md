# P159 – FE: trang Thư viện

| Làn | Tính năng | Phụ thuộc |
|---|---|---|
| FE | F05 | [P153](./P153-error-empty-states.md) |

Dán nguyên khối dưới vào một cửa sổ Claude Code mới mở tại `E:\pm\WriteStoryApp`. Trạng thái của prompt được theo dõi trong [README.md](./README.md#tiến-độ).

```text
[P159] FE: trang Thư viện

Làm theo docs/prompts/README.md mục "Quy tắc chung".
Phụ thuộc phải xong trước: P153. Kiểm tra bảng Tiến độ trong docs/prompts/README.md; nếu chưa xong thì dừng và báo tôi.

Đọc trước:
- docs/steps/TRANG-THAI.md
- docs/implementation-plan.vi.md §24 (bảng quyết định)
- docs/features/F05-thu-vien-va-tao-truyen/fe.md
- docs/ui-design.vi.md §5.1

Việc cần làm:
1. Lưới/bảng có TanStack Virtual, lọc thể loại/trạng thái, tìm Ctrl+K, badge theo compute_library_badge, mở gần đây.
2. Trạng thái rỗng/lỗi/đang tải.
3. Test component.

Phạm vi file: fe/src/features/library/
Xong khi: test pass.

Kết thúc: tick các mục đã làm trong checklist spec liên quan; đổi trạng thái P159 thành done trong bảng Tiến độ của docs/prompts/README.md (đọc lại file ngay trước khi sửa, chỉ sửa dòng P159); cập nhật docs/steps/TRANG-THAI.md; báo cáo theo Quy tắc chung mục 8.
```
