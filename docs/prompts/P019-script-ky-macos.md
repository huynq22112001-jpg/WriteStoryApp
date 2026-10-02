# P019 – Script ký backend cho macOS

| Làn | Tính năng | Phụ thuộc |
|---|---|---|
| DESKTOP | F00 / S09 | [P017](./P017-pyinstaller-onedir.md) |

Dán nguyên khối dưới vào một cửa sổ Claude Code mới mở tại `E:\pm\WriteStoryApp`. Trạng thái của prompt được theo dõi trong [README.md](./README.md#tiến-độ).

```text
[P019] Script ký backend cho macOS

Làm theo docs/prompts/README.md mục "Quy tắc chung".
Phụ thuộc phải xong trước: P017. Kiểm tra bảng Tiến độ trong docs/prompts/README.md; nếu chưa xong thì dừng và báo tôi.

Đọc trước:
- docs/steps/TRANG-THAI.md
- docs/implementation-plan.vi.md §24 (bảng quyết định)
- docs/review-and-optimization.vi.md §7.1
- docs/features/F00-nen-tang-desktop/be.md (mục F.4)

Việc cần làm:
1. `tools/packaging/sign_macos_backend.sh`: codesign --options runtime --timestamp từng Mach-O (.dylib/.so/binary) trong resources/backend bằng Developer ID truyền qua biến môi trường.
2. Ghi hướng dẫn tạo DMG có symlink /Applications vào ADR-003.

Phạm vi file: tools/packaging/, docs/adr/
Xong khi: Script có kiểm tra cú pháp (shellcheck nếu có); chỉ chạy thật khi có máy Mac.

Kết thúc: tick các mục đã làm trong checklist spec liên quan; đổi trạng thái P019 thành done trong bảng Tiến độ của docs/prompts/README.md (đọc lại file ngay trước khi sửa, chỉ sửa dòng P019); cập nhật docs/steps/TRANG-THAI.md; báo cáo theo Quy tắc chung mục 8.
```
