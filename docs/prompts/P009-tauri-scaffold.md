# P009 – Scaffold desktop Tauri 2

| Làn | Tính năng | Phụ thuộc |
|---|---|---|
| DESKTOP | F00 / S07 | [P004](./P004-kiem-chung-fe-base.md) |

Dán nguyên khối dưới vào một cửa sổ Claude Code mới mở tại `E:\pm\WriteStoryApp`. Trạng thái của prompt được theo dõi trong [README.md](./README.md#tiến-độ).

```text
[P009] Scaffold desktop Tauri 2

Làm theo docs/prompts/README.md mục "Quy tắc chung".
Phụ thuộc phải xong trước: P004. Kiểm tra bảng Tiến độ trong docs/prompts/README.md; nếu chưa xong thì dừng và báo tôi.

Đọc trước:
- docs/steps/TRANG-THAI.md
- docs/implementation-plan.vi.md §24 (bảng quyết định)
- docs/steps/S07-desktop-tauri.md
- docs/features/F00-nen-tang-desktop/README.md
- docs/features/F00-nen-tang-desktop/be.md

Việc cần làm:
1. Tạo `desktop/` (package.json với @tauri-apps/cli, thêm `desktop` vào pnpm-workspace.yaml).
2. `desktop/src-tauri/`: Cargo.toml, tauri.conf.json (frontendDist ../../fe/dist, devUrl http://localhost:5173, identifier, CSP theo F00 be.md §C), capabilities/main.json tối thiểu.
3. Đăng ký tauri-plugin-single-instance đầu tiên (mở lần 2 → focus cửa sổ cũ).
4. Chưa spawn backend ở bước này.

Phạm vi file: desktop/, pnpm-workspace.yaml
Xong khi: `pnpm --filter desktop tauri dev` mở cửa sổ hiển thị FE; mở lần hai chỉ focus.

Kết thúc: tick các mục đã làm trong checklist spec liên quan; đổi trạng thái P009 thành done trong bảng Tiến độ của docs/prompts/README.md (đọc lại file ngay trước khi sửa, chỉ sửa dòng P009); cập nhật docs/steps/TRANG-THAI.md; báo cáo theo Quy tắc chung mục 8.
```
