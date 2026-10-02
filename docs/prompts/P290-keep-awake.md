# P290 – DESKTOP: giữ máy thức khi auto-write

| Làn | Tính năng | Phụ thuộc |
|---|---|---|
| DESKTOP | F14 | [P012](./P012-rust-shutdown-commands.md) |

Dán nguyên khối dưới vào một cửa sổ Claude Code mới mở tại `E:\pm\WriteStoryApp`. Trạng thái của prompt được theo dõi trong [README.md](./README.md#tiến-độ).

```text
[P290] DESKTOP: giữ máy thức khi auto-write

Làm theo docs/prompts/README.md mục "Quy tắc chung".
Phụ thuộc phải xong trước: P012. Kiểm tra bảng Tiến độ trong docs/prompts/README.md; nếu chưa xong thì dừng và báo tôi.

Đọc trước:
- docs/steps/TRANG-THAI.md
- docs/implementation-plan.vi.md §24 (bảng quyết định)
- docs/features/F14-thong-bao-nhat-ky-chi-phi/be.md (keep-awake)
- docs/implementation-plan.vi.md §23.2 #9

Việc cần làm:
1. `desktop/src-tauri/src/power.rs`: command set_keep_awake(bool) – Windows SetThreadExecutionState, macOS IOPMAssertion; tự nhả khi app thoát.
2. FE gọi khi có truyện đang chạy và cài đặt cho phép (trễ 30 s trước khi tắt).
3. Test Rust tối thiểu.

Phạm vi file: desktop/src-tauri/src/, fe/src/shared/desktop/
Xong khi: cargo test pass.

Kết thúc: tick các mục đã làm trong checklist spec liên quan; đổi trạng thái P290 thành done trong bảng Tiến độ của docs/prompts/README.md (đọc lại file ngay trước khi sửa, chỉ sửa dòng P290); cập nhật docs/steps/TRANG-THAI.md; báo cáo theo Quy tắc chung mục 8.
```
