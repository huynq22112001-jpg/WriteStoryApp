# P152 – FE: AppShell ribbon/header/status bar

| Làn | Tính năng | Phụ thuộc |
|---|---|---|
| FE | UI | [P151](./P151-font-theme.md) |

Dán nguyên khối dưới vào một cửa sổ Claude Code mới mở tại `E:\pm\WriteStoryApp`. Trạng thái của prompt được theo dõi trong [README.md](./README.md#tiến-độ).

```text
[P152] FE: AppShell ribbon/header/status bar

Làm theo docs/prompts/README.md mục "Quy tắc chung".
Phụ thuộc phải xong trước: P151. Kiểm tra bảng Tiến độ trong docs/prompts/README.md; nếu chưa xong thì dừng và báo tôi.

Đọc trước:
- docs/steps/TRANG-THAI.md
- docs/implementation-plan.vi.md §24 (bảng quyết định)
- docs/ui-design.vi.md §4

Việc cần làm:
1. Ribbon trái (Thư viện, Phòng viết, Cài đặt, Nhật ký), header (breadcrumb, nút Ctrl+K, chỗ chỉ báo 'N truyện đang chạy' và chi phí hôm nay – dữ liệu giả tạm), status bar (backend, slot provider, lưu, ngôn ngữ).
2. Route khung theo UI §4 (trang trống có tiêu đề).
3. Test component.

Phạm vi file: fe/src/app/
Xong khi: test + build pass.

Kết thúc: tick các mục đã làm trong checklist spec liên quan; đổi trạng thái P152 thành done trong bảng Tiến độ của docs/prompts/README.md (đọc lại file ngay trước khi sửa, chỉ sửa dòng P152); cập nhật docs/steps/TRANG-THAI.md; báo cáo theo Quy tắc chung mục 8.
```
