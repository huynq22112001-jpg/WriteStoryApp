# S10 — Kết thúc R0

Trạng thái: nghiệm thu có điều kiện — 1/6 tiêu chí có đủ bằng chứng đạt; 5 tiêu chí chưa đạt/chưa có bằng chứng. Cập nhật: 2026-10-03.

## Checklist (Plan §9 Giai đoạn 0)

- [ ] **Chưa đạt — thiếu bằng chứng máy sạch.** NSIS đã build; chưa cài/chạy trên máy không có Python/Node.
- [ ] **Chưa đạt — thiếu bằng chứng editor.** P008 đã hiển thị stream ở FE; khả năng chạy đồng thời trong WebView mà không chặn editor chưa được đo.
- [ ] **Chưa đạt — thiếu bằng chứng độ mượt.** Ba stream đã smoke-test ở P008, nhưng editor responsiveness chưa được đo cùng lúc.
- [x] Đóng app không để lại tiến trình backend (P012 Windows dev smoke: đóng cửa sổ và kill app dọn backend bằng Job Object; chưa lặp trên installer).
- [ ] **Chưa đạt — thiếu kết quả IME.** Checklist có sẵn, chưa chạy trên Windows WebView2 hoặc macOS WKWebView.
- [ ] **Chưa đạt — thiếu bằng chứng macOS.** Chưa có host macOS để thử data-root khi App Translocation.

## ADR cần viết (`docs/adr/`)

- [x] [ADR-001](../adr/ADR-001-tauri-or-electron.md): quyết định shell còn defer vì chưa có kết quả IME.
- [x] [ADR-002](../adr/ADR-002-spawn-backend.md): onedir trong resources; app startup/RAM đo một mẫu, clean-machine chưa thử.
- [x] [ADR-003](../adr/ADR-003-webview2-macos.md): offlineInstaller và quy trình DMG; clean-machine chưa xác minh.
- [x] [ADR-004](../adr/ADR-004-macos-minimum.md): macOS tối thiểu còn defer đến thử nghiệm thật.

## Sau R0

Bắt đầu R1 theo [features/README.md](../features/README.md#thứ-tự-làm-đề-xuất): F02 (Alembic + baseline + writer queue) → F03 → F05 → F04 → F07.
