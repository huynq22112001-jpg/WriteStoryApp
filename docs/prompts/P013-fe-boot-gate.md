# P013 – FE: BootGate và màn khởi động

| Làn | Tính năng | Phụ thuộc |
|---|---|---|
| FE | F00 | [P012](./P012-rust-shutdown-commands.md), [P004](./P004-kiem-chung-fe-base.md) |

Dán nguyên khối dưới vào một cửa sổ Claude Code mới mở tại `E:\pm\WriteStoryApp`. Trạng thái của prompt được theo dõi trong [README.md](./README.md#tiến-độ).

```text
[P013] FE: BootGate và màn khởi động

Làm theo docs/prompts/README.md mục "Quy tắc chung".
Phụ thuộc phải xong trước: P012, P004. Kiểm tra bảng Tiến độ trong docs/prompts/README.md; nếu chưa xong thì dừng và báo tôi.

Đọc trước:
- docs/steps/TRANG-THAI.md
- docs/implementation-plan.vi.md §24 (bảng quyết định)
- docs/features/F00-nen-tang-desktop/fe.md
- docs/ui-design.vi.md §5.8

Việc cần làm:
1. `fe/src/shared/desktop/bridge.ts`: khi chạy trong Tauri gọi `get_backend_session`; trong trình duyệt giữ nhánh env.
2. `fe/src/app/boot/`: BootGate, useBootState, màn starting / needs_data_root / translocated / startup_error / backend_crashed / banner mất kết nối.
3. Bọc App bằng BootGate; test component cho từng phase (mock bridge).

Phạm vi file: fe/src/shared/desktop/, fe/src/app/boot/, fe/src/app/App.tsx
Xong khi: test + build FE pass.

Kết thúc: tick các mục đã làm trong checklist spec liên quan; đổi trạng thái P013 thành done trong bảng Tiến độ của docs/prompts/README.md (đọc lại file ngay trước khi sửa, chỉ sửa dòng P013); cập nhật docs/steps/TRANG-THAI.md; báo cáo theo Quy tắc chung mục 8.
```
