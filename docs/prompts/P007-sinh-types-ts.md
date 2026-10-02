# P007 – Sinh types TS từ OpenAPI + check_contracts

| Làn | Tính năng | Phụ thuộc |
|---|---|---|
| FE | F01 / S05 | [P006](./P006-xuat-openapi.md), [P004](./P004-kiem-chung-fe-base.md) |

Dán nguyên khối dưới vào một cửa sổ Claude Code mới mở tại `E:\pm\WriteStoryApp`. Trạng thái của prompt được theo dõi trong [README.md](./README.md#tiến-độ).

```text
[P007] Sinh types TS từ OpenAPI + check_contracts

Làm theo docs/prompts/README.md mục "Quy tắc chung".
Phụ thuộc phải xong trước: P006, P004. Kiểm tra bảng Tiến độ trong docs/prompts/README.md; nếu chưa xong thì dừng và báo tôi.

Đọc trước:
- docs/steps/TRANG-THAI.md
- docs/implementation-plan.vi.md §24 (bảng quyết định)
- docs/steps/S05-hop-dong-openapi.md
- docs/features/F01-hop-dong-api-va-su-kien/fe.md

Việc cần làm:
1. `pnpm --filter fe gen:api` → `fe/src/shared/api/generated/schema.d.ts` (banner 'generated – không sửa tay').
2. Đổi `fe/src/shared/api/types.ts` thành re-export từ generated, giữ tên HealthResponse, ErrorResponse, EventEnvelope.
3. Viết `tools/contracts/check_contracts.py`: export + gen rồi fail nếu git diff ở contracts/ và generated/ khác rỗng.

Phạm vi file: fe/src/shared/api/, tools/contracts/
Xong khi: typecheck pass; check_contracts chạy không diff.

Kết thúc: tick các mục đã làm trong checklist spec liên quan; đổi trạng thái P007 thành done trong bảng Tiến độ của docs/prompts/README.md (đọc lại file ngay trước khi sửa, chỉ sửa dòng P007); cập nhật docs/steps/TRANG-THAI.md; báo cáo theo Quy tắc chung mục 8.
```
