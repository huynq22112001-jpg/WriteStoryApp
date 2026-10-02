# P150 – FE: shadcn/ui trên Base UI

| Làn | Tính năng | Phụ thuộc |
|---|---|---|
| FE | UI | [P004](./P004-kiem-chung-fe-base.md) |

Dán nguyên khối dưới vào một cửa sổ Claude Code mới mở tại `E:\pm\WriteStoryApp`. Trạng thái của prompt được theo dõi trong [README.md](./README.md#tiến-độ).

```text
[P150] FE: shadcn/ui trên Base UI

Làm theo docs/prompts/README.md mục "Quy tắc chung".
Phụ thuộc phải xong trước: P004. Kiểm tra bảng Tiến độ trong docs/prompts/README.md; nếu chưa xong thì dừng và báo tôi.

Đọc trước:
- docs/steps/TRANG-THAI.md
- docs/implementation-plan.vi.md §24 (bảng quyết định)
- docs/ui-design.vi.md §3

Việc cần làm:
1. `pnpm dlx shadcn@latest init` trong fe/, chọn Base UI, Tailwind v4, alias @/.
2. Thêm component: button, input, label, dialog, dropdown-menu, tabs, tooltip, sonner, command, resizable, sidebar, badge, skeleton, switch, select.
3. Trang /system dùng thử vài component.

Phạm vi file: fe/
Xong khi: typecheck, test, build pass.

Kết thúc: tick các mục đã làm trong checklist spec liên quan; đổi trạng thái P150 thành done trong bảng Tiến độ của docs/prompts/README.md (đọc lại file ngay trước khi sửa, chỉ sửa dòng P150); cập nhật docs/steps/TRANG-THAI.md; báo cáo theo Quy tắc chung mục 8.
```
