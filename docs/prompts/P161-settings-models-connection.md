# P161 – FE: Cài đặt Mô hình AI – kết nối + lấy danh sách

| Làn | Tính năng | Phụ thuộc |
|---|---|---|
| FE | F04 | [P153](./P153-error-empty-states.md) |

Dán nguyên khối dưới vào một cửa sổ Claude Code mới mở tại `E:\pm\WriteStoryApp`. Trạng thái của prompt được theo dõi trong [README.md](./README.md#tiến-độ).

```text
[P161] FE: Cài đặt Mô hình AI – kết nối + lấy danh sách

Làm theo docs/prompts/README.md mục "Quy tắc chung".
Phụ thuộc phải xong trước: P153. Kiểm tra bảng Tiến độ trong docs/prompts/README.md; nếu chưa xong thì dừng và báo tôi.

Đọc trước:
- docs/steps/TRANG-THAI.md
- docs/implementation-plan.vi.md §24 (bảng quyết định)
- docs/features/F04-cau-hinh-mo-hinh-ai/fe.md
- docs/ui-design.vi.md §5.6.1
- docs/tests/flows/T03-cau-hinh-mo-hinh-ai.md

Việc cần làm:
1. /settings/models: giao thức, Base URL, API key, nút 'Kiểm tra lấy danh sách' có chấm trạng thái + lỗi cụ thể, công tắc tự lấy danh sách, công tắc context 1M (ẩn khi không áp dụng – D28).
2. Mẫu mỗi mục: tiêu đề đậm, mô tả xám, 'Tìm hiểu thêm ⌄', điều khiển bên phải; lưu tự động + toast.
3. Bộ chuyển provider khi có nhiều provider (D27).
4. Test.

Phạm vi file: fe/src/features/settings/models/
Xong khi: test pass.

Kết thúc: tick các mục đã làm trong checklist spec liên quan; đổi trạng thái P161 thành done trong bảng Tiến độ của docs/prompts/README.md (đọc lại file ngay trước khi sửa, chỉ sửa dòng P161); cập nhật docs/steps/TRANG-THAI.md; báo cáo theo Quy tắc chung mục 8.
```
