# S10 — Kết thúc R0

Trạng thái: todo. Phụ thuộc: S00–S09.

## Checklist (Plan §9 Giai đoạn 0)

- [ ] Máy sạch không có Python/Node mở được app (S09).
- [ ] Mock stream AI hiển thị trên FE qua `/v1/events`, không chặn editor (S06, S08).
- [ ] Thử 3 truyện mock stream song song (`POST /v1/dev/mock-runs`, F00) – editor vẫn gõ mượt.
- [ ] Đóng app không để lại tiến trình backend (S07).
- [ ] Gõ tiếng Việt ổn định trên cả hai WebView (S08).
- [ ] Luồng data-root macOS khi bị App Translocation (S07).

## ADR cần viết (`docs/adr/`)

- [ ] ADR-001 Giữ Tauri hay đổi Electron (dựa trên S08).
- [ ] ADR-002 Cách spawn backend: onedir trong resources (D22).
- [ ] ADR-003 Chế độ WebView2 cho installer và bản zip (D20).
- [ ] ADR-004 Phiên bản macOS tối thiểu.

## Sau R0

Bắt đầu R1 theo [features/README.md](../features/README.md#thứ-tự-làm-đề-xuất): F02 (Alembic + baseline + writer queue) → F03 → F05 → F04 → F07.
