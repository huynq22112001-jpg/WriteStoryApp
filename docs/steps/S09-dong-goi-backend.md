# S09 — Đóng gói backend Python

Trạng thái: todo. Tính năng: F00. Phụ thuộc: S03, S07.

## Mục tiêu

Máy sạch (không có Python/Node) chạy được app (Plan §9 Giai đoạn 0).

## Việc cần làm

- [ ] `tools/packaging/backend.spec`: PyInstaller **onedir**, tên `writestory-backend`, gom package data của `writestory_ai` (prompts, gói ngôn ngữ) và migrations BE; hidden imports (`aiosqlite`, provider registry).
- [ ] `tools/packaging/build_backend.py`: `uv sync --frozen` → PyInstaller → copy vào `desktop/src-tauri/resources/backend/`.
- [ ] `tauri.conf.json`: `bundle.resources` dạng thư mục `"resources/backend/"` (Review §7.1); Rust spawn trực tiếp binary trong resource dir (D22).
- [ ] Windows: thử installer `offlineInstaller` và zip portable với WebView2 có sẵn / `fixedRuntime` (D20).
- [ ] macOS: `sign_macos_backend.sh` ký từng `.dylib/.so` trước `tauri build`; DMG có symlink `/Applications`.
- [ ] Đo: dung lượng bundle, thời gian khởi động lạnh tới `ready`, RAM idle.

## Tiêu chí xong

Bản build mở trên máy sạch Windows x64 và macOS arm64; số đo được ghi vào ADR.
