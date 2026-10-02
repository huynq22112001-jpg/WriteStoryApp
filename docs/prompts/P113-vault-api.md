# P113 – API vault + secrets + event vault.status

| Làn | Tính năng | Phụ thuộc |
|---|---|---|
| BE | F03 | [P112](./P112-secret-store.md), [P108](./P108-eventbus-db.md) |

Dán nguyên khối dưới vào một cửa sổ Claude Code mới mở tại `E:\pm\WriteStoryApp`. Trạng thái của prompt được theo dõi trong [README.md](./README.md#tiến-độ).

```text
[P113] API vault + secrets + event vault.status

Làm theo docs/prompts/README.md mục "Quy tắc chung".
Phụ thuộc phải xong trước: P112, P108. Kiểm tra bảng Tiến độ trong docs/prompts/README.md; nếu chưa xong thì dừng và báo tôi.

Đọc trước:
- docs/steps/TRANG-THAI.md
- docs/implementation-plan.vi.md §24 (bảng quyết định)
- docs/features/F03-khoi-dau-va-vault/be.md (bảng API)
- docs/implementation-plan.vi.md §24 D9

Việc cần làm:
1. `modules/vault/`: POST /v1/vault, unlock, lock, status, change-password, reset, PUT mode; GET/PUT/DELETE /v1/secrets.
2. Event `vault.status`; mã VAULT_LOCKED (423) cho lời gọi đồng bộ cần key.
3. Test theo bảng F03 be.md.

Phạm vi file: be/src/writestory_be/modules/vault/, be/src/writestory_be/main.py (đăng ký router), be/tests/
Xong khi: Test pass.

Kết thúc: tick các mục đã làm trong checklist spec liên quan; đổi trạng thái P113 thành done trong bảng Tiến độ của docs/prompts/README.md (đọc lại file ngay trước khi sửa, chỉ sửa dòng P113); cập nhật docs/steps/TRANG-THAI.md; báo cáo theo Quy tắc chung mục 8.
```
