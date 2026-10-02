# P016 – Chuẩn bị kiểm tra bộ gõ tiếng Việt

| Làn | Tính năng | Phụ thuộc |
|---|---|---|
| FE | F07 / S08 | [P015](./P015-paste-nfc-dem-am-tiet-ts.md), [P013](./P013-fe-boot-gate.md) |

Dán nguyên khối dưới vào một cửa sổ Claude Code mới mở tại `E:\pm\WriteStoryApp`. Trạng thái của prompt được theo dõi trong [README.md](./README.md#tiến-độ).

```text
[P016] Chuẩn bị kiểm tra bộ gõ tiếng Việt

Làm theo docs/prompts/README.md mục "Quy tắc chung".
Phụ thuộc phải xong trước: P015, P013. Kiểm tra bảng Tiến độ trong docs/prompts/README.md; nếu chưa xong thì dừng và báo tôi.

Đọc trước:
- docs/steps/TRANG-THAI.md
- docs/implementation-plan.vi.md §24 (bảng quyết định)
- docs/tests/flows/T12-editor-autosave-ime.md
- docs/features/F07-editor-va-phien-ban/fe.md (IME-01…IME-12)

Việc cần làm:
1. Viết `docs/tests/manual/ime-checklist.md`: từng bước gõ cho Unikey, EVKey (bật/tắt sửa lỗi gợi ý), Telex/VNI macOS; trong bold/italic, đầu/cuối mark, undo/redo, paste Word.
2. Thêm nút bật bold/italic trên trang /editor-spike để thử.
3. KHÔNG tự đánh dấu pass ô thủ công – để tôi gõ thử và điền.

Phạm vi file: docs/tests/manual/, fe/src/features/editor/
Xong khi: Checklist sẵn sàng để tôi chạy trong `tauri dev`.

Kết thúc: tick các mục đã làm trong checklist spec liên quan; đổi trạng thái P016 thành done trong bảng Tiến độ của docs/prompts/README.md (đọc lại file ngay trước khi sửa, chỉ sửa dòng P016); cập nhật docs/steps/TRANG-THAI.md; báo cáo theo Quy tắc chung mục 8.
```
