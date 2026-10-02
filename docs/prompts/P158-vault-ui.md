# P158 – FE: mở khóa vault + trang Bảo mật

| Làn | Tính năng | Phụ thuộc |
|---|---|---|
| FE | F03 | [P153](./P153-error-empty-states.md) |

Dán nguyên khối dưới vào một cửa sổ Claude Code mới mở tại `E:\pm\WriteStoryApp`. Trạng thái của prompt được theo dõi trong [README.md](./README.md#tiến-độ).

```text
[P158] FE: mở khóa vault + trang Bảo mật

Làm theo docs/prompts/README.md mục "Quy tắc chung".
Phụ thuộc phải xong trước: P153. Kiểm tra bảng Tiến độ trong docs/prompts/README.md; nếu chưa xong thì dừng và báo tôi.

Đọc trước:
- docs/steps/TRANG-THAI.md
- docs/implementation-plan.vi.md §24 (bảng quyết định)
- docs/features/F03-khoi-dau-va-vault/fe.md

Việc cần làm:
1. VaultUnlockDialog (mở khi gặp VAULT_LOCKED hoặc event vault.status), VaultBadge ở header.
2. /settings/security: tạo vault, đổi mật khẩu, đặt lại, danh sách secret (không hiện giá trị).
3. Test.

Phạm vi file: fe/src/features/vault/, fe/src/features/settings/security*
Xong khi: test pass.

Kết thúc: tick các mục đã làm trong checklist spec liên quan; đổi trạng thái P158 thành done trong bảng Tiến độ của docs/prompts/README.md (đọc lại file ngay trước khi sửa, chỉ sửa dòng P158); cập nhật docs/steps/TRANG-THAI.md; báo cáo theo Quy tắc chung mục 8.
```
