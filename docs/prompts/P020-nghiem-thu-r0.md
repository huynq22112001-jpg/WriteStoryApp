# P020 – Nghiệm thu R0 + ADR

| Làn | Tính năng | Phụ thuộc |
|---|---|---|
| Tất cả | S10 | [P008](./P008-script-dev-va-readme.md), [P013](./P013-fe-boot-gate.md), [P016](./P016-checklist-ime.md), [P018](./P018-gan-backend-vao-tauri.md) |

Dán nguyên khối dưới vào một cửa sổ Claude Code mới mở tại `E:\pm\WriteStoryApp`. Trạng thái của prompt được theo dõi trong [README.md](./README.md#tiến-độ).

```text
[P020] Nghiệm thu R0 + ADR

Làm theo docs/prompts/README.md mục "Quy tắc chung".
Phụ thuộc phải xong trước: P008, P013, P016, P018. Kiểm tra bảng Tiến độ trong docs/prompts/README.md; nếu chưa xong thì dừng và báo tôi.

Đọc trước:
- docs/steps/TRANG-THAI.md
- docs/implementation-plan.vi.md §24 (bảng quyết định)
- docs/steps/S10-ket-thuc-r0.md
- docs/tests/manual/ime-checklist.md (kết quả tôi đã điền)

Việc cần làm:
1. Chạy lại mọi test (AI, BE, FE, cargo).
2. Đánh giá từng ô checklist S10 bằng bằng chứng thật; ô thiếu bằng chứng ghi 'chưa đạt' + lý do.
3. Viết ADR-001 (Tauri hay Electron, dựa trên kết quả IME), ADR-003 (WebView2), ADR-004 (macOS tối thiểu).

Phạm vi file: docs/adr/, docs/steps/
Xong khi: S10 có trạng thái thật cho mọi ô.

Kết thúc: tick các mục đã làm trong checklist spec liên quan; đổi trạng thái P020 thành done trong bảng Tiến độ của docs/prompts/README.md (đọc lại file ngay trước khi sửa, chỉ sửa dòng P020); cập nhật docs/steps/TRANG-THAI.md; báo cáo theo Quy tắc chung mục 8.
```
