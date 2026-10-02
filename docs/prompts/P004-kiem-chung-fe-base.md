# P004 – Kiểm chứng code base FE

| Làn | Tính năng | Phụ thuộc |
|---|---|---|
| FE | S04 | — |

Dán nguyên khối dưới vào một cửa sổ Claude Code mới mở tại `E:\pm\WriteStoryApp`. Trạng thái của prompt được theo dõi trong [README.md](./README.md#tiến-độ).

```text
[P004] Kiểm chứng code base FE

Làm theo docs/prompts/README.md mục "Quy tắc chung".
Phụ thuộc phải xong trước: không có. Kiểm tra bảng Tiến độ trong docs/prompts/README.md; nếu chưa xong thì dừng và báo tôi.

Đọc trước:
- docs/steps/TRANG-THAI.md
- docs/implementation-plan.vi.md §24 (bảng quyết định)
- docs/steps/TRANG-THAI.md
- docs/steps/S04-base-fe.md
- docs/features/F01-hop-dong-api-va-su-kien/fe.md

Việc cần làm:
1. `pnpm --filter fe typecheck`, `pnpm --filter fe test`, `pnpm --filter fe build` – sửa cho pass.
2. Thêm khóa `PROVIDER_SERVER_ERROR` vào `fe/src/shared/i18n/vi/errors.json`.

Phạm vi file: fe/
Xong khi: typecheck, test, build của fe pass.

Kết thúc: tick các mục đã làm trong checklist spec liên quan; đổi trạng thái P004 thành done trong bảng Tiến độ của docs/prompts/README.md (đọc lại file ngay trước khi sửa, chỉ sửa dòng P004); cập nhật docs/steps/TRANG-THAI.md; báo cáo theo Quy tắc chung mục 8.
```
