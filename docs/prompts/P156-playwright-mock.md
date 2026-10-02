# P156 – FE: Playwright + backend giả

| Làn | Tính năng | Phụ thuộc |
|---|---|---|
| FE | Test | [P152](./P152-app-shell.md) |

Dán nguyên khối dưới vào một cửa sổ Claude Code mới mở tại `E:\pm\WriteStoryApp`. Trạng thái của prompt được theo dõi trong [README.md](./README.md#tiến-độ).

```text
[P156] FE: Playwright + backend giả

Làm theo docs/prompts/README.md mục "Quy tắc chung".
Phụ thuộc phải xong trước: P152. Kiểm tra bảng Tiến độ trong docs/prompts/README.md; nếu chưa xong thì dừng và báo tôi.

Đọc trước:
- docs/steps/TRANG-THAI.md
- docs/implementation-plan.vi.md §24 (bảng quyết định)
- docs/tests/README.md (cấp e2e-fe)

Việc cần làm:
1. Cài Playwright, cấu hình chạy Vite dev.
2. Backend giả trong `fe/tests/mocks/` (route giả /v1/health, /v1/events SSE, dữ liệu mẫu) dùng chung cho e2e.
3. 1 test e2e: mở thư viện, mở trang hệ thống thấy 'Hoạt động bình thường'.

Phạm vi file: fe/tests/, fe/playwright.config.ts, fe/package.json
Xong khi: `pnpm --filter fe exec playwright test` pass.

Kết thúc: tick các mục đã làm trong checklist spec liên quan; đổi trạng thái P156 thành done trong bảng Tiến độ của docs/prompts/README.md (đọc lại file ngay trước khi sửa, chỉ sửa dòng P156); cập nhật docs/steps/TRANG-THAI.md; báo cáo theo Quy tắc chung mục 8.
```
