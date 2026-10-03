# S09 — Đóng gói backend Python

Trạng thái: Windows onedir + NSIS build đã xong; cài trên máy sạch và kiểm tra macOS còn thiếu. Tính năng: F00. Phụ thuộc: S03, S07.

## Mục tiêu

Máy sạch (không có Python/Node) chạy được app (Plan §9 Giai đoạn 0).

## Việc cần làm

- [x] `tools/packaging/backend.spec`: PyInstaller **onedir**, tên `writestory-backend`, gom package data của `writestory_ai` và migrations BE; hidden imports gồm `aiosqlite` và provider modules.
- [x] `tools/packaging/build_backend.py`: `uv sync --frozen` → PyInstaller → copy vào `desktop/src-tauri/resources/backend/`.
- [x] `tauri.conf.json`: `bundle.resources` dạng thư mục `"resources/backend/"`; Rust release spawn binary từ resources. Build NSIS `offlineInstaller` pass.
- [ ] Cài/chạy NSIS trên máy sạch và thử zip portable với WebView2 có sẵn / `fixedRuntime` (D20). Installer 230.11 MiB đã build nhưng chưa cài trên host sạch.
- [x] Tạo `sign_macos_backend.sh` và hướng dẫn DMG có symlink `/Applications` trong ADR-003. Script chưa chạy trên macOS.
- [x] Đo ở Windows dev host: onedir 52.17 MiB; NSIS 230.11 MiB; lần đầu tới ready 6.74 s, lần sau 1.56 s; working set sau 5 s idle: app 26.6 MiB + backend 110.9 MiB. Một mẫu; chưa phải clean-machine/performance benchmark.

## Tiêu chí xong

Bản build mở trên máy sạch Windows x64 và macOS arm64; số đo được ghi vào ADR.
