# P010 – Rust: data-root + khóa instance

| Làn | Tính năng | Phụ thuộc |
|---|---|---|
| DESKTOP | F00 | [P009](./P009-tauri-scaffold.md) |

Dán nguyên khối dưới vào một cửa sổ Claude Code mới mở tại `E:\pm\WriteStoryApp`. Trạng thái của prompt được theo dõi trong [README.md](./README.md#tiến-độ).

```text
[P010] Rust: data-root + khóa instance

Làm theo docs/prompts/README.md mục "Quy tắc chung".
Phụ thuộc phải xong trước: P009. Kiểm tra bảng Tiến độ trong docs/prompts/README.md; nếu chưa xong thì dừng và báo tôi.

Đọc trước:
- docs/steps/TRANG-THAI.md
- docs/implementation-plan.vi.md §24 (bảng quyết định)
- docs/features/F00-nen-tang-desktop/be.md
- docs/implementation-plan.vi.md §3.1, §24 D20, D21, D24
- docs/tests/flows/T01-khoi-dong-va-data-root.md

Việc cần làm:
1. `src/data_root.rs`: Windows cạnh .exe / con trỏ %APPDATA% khi không ghi được; macOS con trỏ + phát hiện `/AppTranslocation/`; kiểm tra ghi thật, ổ mạng, cloud sync; marker `.writestory-data.json`; env WRITESTORY_DATA_ROOT chỉ ở debug.
2. `src/instance_lock.rs`: khóa OS `data/.instance.lock` (crate fs4).
3. `src/boot_state.rs`: BootState + event `boot:state`.
4. Unit test (trừu tượng hóa FS/current_exe): writable, unwritable, translocated, mismatch, ổ mạng.

Phạm vi file: desktop/src-tauri/src/
Xong khi: `cargo test` pass.

Kết thúc: tick các mục đã làm trong checklist spec liên quan; đổi trạng thái P010 thành done trong bảng Tiến độ của docs/prompts/README.md (đọc lại file ngay trước khi sửa, chỉ sửa dòng P010); cập nhật docs/steps/TRANG-THAI.md; báo cáo theo Quy tắc chung mục 8.
```
