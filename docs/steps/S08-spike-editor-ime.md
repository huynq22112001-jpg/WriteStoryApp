# S08 — Spike editor Tiptap + bộ gõ tiếng Việt

Trạng thái: doing — editor spike, NFC paste và đếm âm tiết đã triển khai; checklist IME chờ chạy thủ công. Tính năng: F07. Phụ thuộc: S04 (S07 để test trong WebView thật).

## Mục tiêu

Chứng minh editor gõ tiếng Việt ổn định trên WebView2 (Windows) và WKWebView (macOS) trước khi xây tính năng lớn (Plan §9 Giai đoạn 0). Đây là điểm quyết định giữ Tauri hay đổi sang Electron.

## Việc cần làm

- [x] Cài Tiptap v3 (`@tiptap/react`, `starter-kit`, `@tiptap/extensions`, `extension-unique-id`), pin `prosemirror-view` ≥ 1.41.9.
- [x] `fe/src/features/editor/` tối thiểu: editor một chương, `paragraph_id` 8 ký tự `[a-z0-9]` (D19); đếm âm tiết bằng cùng thuật toán gói `vi`.
- [x] Paste text/HTML chuẩn hóa NFC, line ending và khoảng trắng theo tiện ích gói `vi`.
- [ ] Chạy checklist IME thủ công trong [T12](../tests/flows/T12-editor-autosave-ime.md): Unikey, EVKey (bật/tắt "sửa lỗi gợi ý"), Telex/VNI macOS; gõ trong bold/italic, đầu/cuối mark, undo/redo.
- [ ] Ghi kết quả từng ô vào T12 và ADR.

Checklist chạy thủ công đã được chuẩn bị tại [ime-checklist.md](../tests/manual/ime-checklist.md). Kết quả Windows/macOS vẫn chưa có.

## Tiêu chí xong

Không mất/nhân đôi ký tự trong mọi ô checklist trên cả hai WebView; hoặc có ADR quyết định đổi shell.
